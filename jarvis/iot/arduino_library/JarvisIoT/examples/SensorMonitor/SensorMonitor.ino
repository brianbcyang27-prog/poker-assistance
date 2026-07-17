/*
 * SensorMonitor.ino — JARVIS IoT sensor monitoring example.
 * 
 * Reads temperature, humidity (DHT22), and light level (analog).
 * JARVIS can query these sensors at any time.
 *
 * Circuit:
 *   DHT22 data → GPIO 4
 *   LDR → GPIO 34 (analog)
 */

#include <JarvisIoT.h>
#include <DHT.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22
#define LDR_PIN 34

DHT dht(DHT_PIN, DHT_TYPE);

JarvisIoT jarvis(
    "Environment Sensor",
    "YOUR_WIFI_SSID",
    "YOUR_WIFI_PASSWORD"
);

void setup() {
    Serial.begin(115200);
    dht.begin();
    pinMode(LDR_PIN, INPUT);
    
    jarvis.begin();
    
    // Register sensors — JARVIS can read these
    jarvis.addSensor("temperature", []() {
        float t = dht.readTemperature();
        return isnan(t) ? "error" : String(t, 1);
    });
    
    jarvis.addSensor("humidity", []() {
        float h = dht.readHumidity();
        return isnan(h) ? "error" : String(h, 1);
    });
    
    jarvis.addSensor("light", []() {
        int raw = analogRead(LDR_PIN);
        return String(raw);
    });
    
    jarvis.addSensor("heat_index", []() {
        float t = dht.readTemperature();
        float h = dht.readHumidity();
        if (isnan(t) || isnan(h)) return "error";
        float hi = dht.computeHeatIndex(t, h, false);
        return String(hi, 1);
    });
    
    // Register a command to get all readings at once
    jarvis.onCommand("read_all", [](JsonDocument& p, JsonDocument& r) {
        float t = dht.readTemperature();
        float h = dht.readHumidity();
        int light = analogRead(LDR_PIN);
        
        r["status"] = "ok";
        r["data"]["temperature"] = isnan(t) ? "error" : t;
        r["data"]["humidity"] = isnan(h) ? "error" : h;
        r["data"]["light"] = light;
        r["data"]["heat_index"] = isnan(t) || isnan(h) ? "error" : 
            dht.computeHeatIndex(t, h, false);
    });
    
    jarvis.setMetadata("board", "ESP32");
    jarvis.setMetadata("sensors", "dht22,ldr");
    jarvis.setMetadata("location", "workshop");
    
    jarvis.registerWith("192.168.1.100", 8000);
}

void loop() {
    jarvis.update();
}
