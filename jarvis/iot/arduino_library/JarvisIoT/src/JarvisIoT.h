/*
 * JarvisIoT.h — Arduino/ESP32 library for JARVIS IoT integration.
 *
 * Include this in your ESP32 project to make it discoverable and
 * controllable by JARVIS over WiFi.
 *
 * Usage:
 *   #include <JarvisIoT.h>
 *
 *   JarvisIoT jarvis("MyDevice", "WiFi_SSID", "WiFi_PASSWORD");
 *
 *   void setup() {
 *       jarvis.begin();
 *       jarvis.onCommand("ledon", []{ digitalWrite(LED, HIGH); });
 *       jarvis.onCommand("ledoff", []{ digitalWrite(LED, LOW); });
 *       jarvis.addSensor("temperature", []{ return String(analogRead(A0)); });
 *   }
 *
 *   void loop() {
 *       jarvis.update();
 *   }
 *
 * Protocol: HTTP JSON on port 80.
 * JARVIS sends: {"cmd":"ledon","payload":{},"id":"abc123"}
 * ESP32 responds: {"status":"ok","data":{},"id":"abc123"}
 */

#ifndef JARVIS_IOT_H
#define JARVIS_IOT_H

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <mDNS.h>

// Callback types
typedef void (*CommandCallback)(JsonDocument& payload, JsonDocument& response);
typedef String (*SensorCallback)();

class JarvisIoT {
public:
    /**
     * Create a JARVIS IoT device.
     * @param deviceName  Human-readable name (e.g., "Workshop LED Strip")
     * @param ssid        WiFi network name
     * @param password    WiFi password
     * @param port        HTTP server port (default 80)
     */
    JarvisIoT(const char* deviceName, const char* ssid, const char* password, int port = 80);

    /** Initialize WiFi, mDNS, and HTTP server. Call in setup(). */
    void begin();

    /** Call in loop() to handle HTTP requests and maintain connections. */
    void update();

    /** Register a command handler. */
    void onCommand(const char* command, CommandCallback callback);

    /** Register a sensor reader. */
    void addSensor(const char* sensorName, SensorCallback callback);

    /** Register an actuator (for JARVIS to know what's controllable). */
    void addActuator(const char* actuatorName);

    /** Set device metadata (sent to JARVIS on registration). */
    void setMetadata(const char* key, const char* value);

    /** Get the device's IP address. */
    String getIP();

    /** Check if WiFi is connected. */
    bool isConnected();

    /** Manually register with JARVIS server. */
    bool registerWith(const char* jarvisHost, int jarvisPort = 8000);

    /** Send an event/notification to JARVIS. */
    bool notify(const char* event, const char* data);

    /** Get device ID (MAC address based). */
    String getDeviceId();

private:
    void _handleRoot();
    void _handleJarvis();
    void _handleStatus();
    void _setupMDNS();
    void _registerCapabilities();

    const char* _deviceName;
    const char* _ssid;
    const char* _password;
    int _port;
    String _deviceId;

    WebServer* _server;
    CommandCallback _commandCallbacks[32];
    const char* _commandNames[32];
    int _commandCount = 0;

    SensorCallback _sensorCallbacks[16];
    const char* _sensorNames[16];
    int _sensorCount = 0;

    const char* _actuators[16];
    int _actuatorCount = 0;

    const char* _metadataKeys[8];
    const char* _metadataValues[8];
    int _metadataCount = 0;
};

#endif // JARVIS_IOT_H
