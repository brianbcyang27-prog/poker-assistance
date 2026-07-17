/*
 * JarvisIoT.cpp — Implementation of JARVIS IoT library for ESP32.
 */

#include "JarvisIoT.h"
#include <WiFi.h>
#include <HTTPClient.h>

JarvisIoT::JarvisIoT(const char* deviceName, const char* ssid, const char* password, int port)
    : _deviceName(deviceName), _ssid(ssid), _password(password), _port(port),
      _commandCount(0), _sensorCount(0), _actuatorCount(0), _metadataCount(0) {
    
    // Generate device ID from MAC
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char id[16];
    snprintf(id, sizeof(id), "esp32_%02x%02x%02x", mac[3], mac[4], mac[5]);
    _deviceId = String(id);
}

void JarvisIoT::begin() {
    // Connect to WiFi
    Serial.printf("[JarvisIoT] Connecting to %s", _ssid);
    WiFi.begin(_ssid, _password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[JarvisIoT] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[JarvisIoT] WiFi connection failed!");
        return;
    }
    
    // Setup mDNS
    _setupMDNS();
    
    // Setup HTTP server
    _server = new WebServer(_port);
    
    _server->on("/", HTTP_GET, [this]() { _handleRoot(); });
    _server->on("/jarvis", HTTP_POST, [this]() { _handleJarvis(); });
    _server->on("/status", HTTP_GET, [this]() { _handleStatus(); });
    
    _server->begin();
    Serial.printf("[JarvisIoT] HTTP server started on port %d\n", _port);
    
    // Register built-in commands
    onCommand("ping", [](JsonDocument& p, JsonDocument& r) {
        r["status"] = "ok";
        r["data"]["pong"] = true;
    });
    
    onCommand("identify", [this](JsonDocument& p, JsonDocument& r) {
        r["status"] = "ok";
        r["data"]["name"] = _deviceName;
        r["data"]["id"] = _deviceId;
        r["data"]["ip"] = WiFi.localIP().toString();
        r["data"]["uptime"] = millis() / 1000;
    });
}

void JarvisIoT::update() {
    if (_server) {
        _server->handleClient();
    }
}

void JarvisIoT::onCommand(const char* command, CommandCallback callback) {
    if (_commandCount < 32) {
        _commandNames[_commandCount] = command;
        _commandCallbacks[_commandCount] = callback;
        _commandCount++;
    }
}

void JarvisIoT::addSensor(const char* sensorName, SensorCallback callback) {
    if (_sensorCount < 16) {
        _sensorNames[_sensorCount] = sensorName;
        _sensorCallbacks[_sensorCount] = callback;
        _sensorCount++;
    }
}

void JarvisIoT::addActuator(const char* actuatorName) {
    if (_actuatorCount < 16) {
        _actuators[_actuatorCount] = actuatorName;
        _actuatorCount++;
    }
}

void JarvisIoT::setMetadata(const char* key, const char* value) {
    if (_metadataCount < 8) {
        _metadataKeys[_metadataCount] = key;
        _metadataValues[_metadataCount] = value;
        _metadataCount++;
    }
}

String JarvisIoT::getIP() {
    return WiFi.localIP().toString();
}

bool JarvisIoT::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

String JarvisIoT::getDeviceId() {
    return _deviceId;
}

void JarvisIoT::_setupMDNS() {
    if (MDNS.begin(_deviceId.c_str())) {
        MDNS.addService("jarvis-iot", "tcp", _port);
        MDNS.addServiceTxt("jarvis-iot", "tcp", "id", _deviceId.c_str());
        MDNS.addServiceTxt("jarvis-iot", "tcp", "name", _deviceName);
        Serial.printf("[JarvisIoT] mDNS: %s.local\n", _deviceId.c_str());
    }
}

void JarvisIoT::_handleRoot() {
    StaticJsonDocument<512> doc;
    doc["device_id"] = _deviceId;
    doc["name"] = _deviceName;
    doc["ip"] = WiFi.localIP().toString();
    doc["uptime"] = millis() / 1000;
    
    JsonArray cmds = doc.createNestedArray("commands");
    for (int i = 0; i < _commandCount; i++) {
        cmds.add(_commandNames[i]);
    }
    
    JsonArray snsrs = doc.createNestedArray("sensors");
    for (int i = 0; i < _sensorCount; i++) {
        snsrs.add(_sensorNames[i]);
    }
    
    JsonArray acts = doc.createNestedArray("actuators");
    for (int i = 0; i < _actuatorCount; i++) {
        acts.add(_actuators[i]);
    }
    
    String response;
    serializeJson(doc, response);
    _server->send(200, "application/json", response);
}

void JarvisIoT::_handleJarvis() {
    String body = _server->arg("plain");
    
    StaticJsonDocument<512> request;
    DeserializationError error = deserializeJson(request, body);
    
    if (error) {
        _server->send(400, "application/json", "{\"status\":\"error\",\"data\":{\"message\":\"Invalid JSON\"}}");
        return;
    }
    
    const char* cmd = request["cmd"];
    const char* id = request["id"];
    JsonObject payload = request["payload"];
    
    // Build response
    StaticJsonDocument<512> response;
    response["id"] = id ? id : "";
    
    if (!cmd) {
        response["status"] = "error";
        response["data"]["message"] = "No command specified";
    } else {
        bool found = false;
        for (int i = 0; i < _commandCount; i++) {
            if (strcmp(_commandNames[i], cmd) == 0) {
                _commandCallbacks[i](payload, response);
                found = true;
                break;
            }
        }
        
        // Built-in sensor read command
        if (!found && strcmp(cmd, "read_sensor") == 0) {
            const char* sensor = payload["sensor"];
            if (sensor) {
                for (int i = 0; i < _sensorCount; i++) {
                    if (strcmp(_sensorNames[i], sensor) == 0) {
                        String value = _sensorCallbacks[i]();
                        response["status"] = "ok";
                        response["data"]["value"] = value;
                        found = true;
                        break;
                    }
                }
            }
            if (!found) {
                response["status"] = "error";
                response["data"]["message"] = "Sensor not found";
            }
        } else if (!found) {
            response["status"] = "error";
            response["data"]["message"] = "Unknown command";
        }
    }
    
    String responseStr;
    serializeJson(response, responseStr);
    _server->send(200, "application/json", responseStr);
}

void JarvisIoT::_handleStatus() {
    StaticJsonDocument<256> doc;
    doc["device_id"] = _deviceId;
    doc["name"] = _deviceName;
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    doc["uptime"] = millis() / 1000;
    doc["free_heap"] = ESP.getFreeHeap();
    doc["commands"] = _commandCount;
    doc["sensors"] = _sensorCount;
    
    String response;
    serializeJson(doc, response);
    _server->send(200, "application/json", response);
}

bool JarvisIoT::registerWith(const char* jarvisHost, int jarvisPort) {
    if (!isConnected()) return false;
    
    HTTPClient http;
    String url = String("http://") + jarvisHost + ":" + jarvisPort + "/api/iot/register";
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    // Build registration payload
    StaticJsonDocument<1024> doc;
    doc["device_id"] = _deviceId;
    doc["name"] = _deviceName;
    doc["ip"] = WiFi.localIP().toString();
    doc["port"] = _port;
    
    JsonArray caps = doc.createNestedArray("capabilities");
    for (int i = 0; i < _commandCount; i++) {
        caps.add(_commandNames[i]);
    }
    
    JsonArray snsrs = doc.createNestedArray("sensors");
    for (int i = 0; i < _sensorCount; i++) {
        snsrs.add(_sensorNames[i]);
    }
    
    JsonArray acts = doc.createNestedArray("actuators");
    for (int i = 0; i < _actuatorCount; i++) {
        acts.add(_actuators[i]);
    }
    
    JsonObject meta = doc.createNestedObject("metadata");
    for (int i = 0; i < _metadataCount; i++) {
        meta[_metadataKeys[i]] = _metadataValues[i];
    }
    
    String payload;
    serializeJson(doc, payload);
    
    int code = http.POST(payload);
    http.end();
    
    return code == 200;
}

bool JarvisIoT::notify(const char* event, const char* data) {
    // Notify via a registered JARVIS host (if known)
    // For now, just log it
    Serial.printf("[JarvisIoT] Event: %s — %s\n", event, data);
    return true;
}
