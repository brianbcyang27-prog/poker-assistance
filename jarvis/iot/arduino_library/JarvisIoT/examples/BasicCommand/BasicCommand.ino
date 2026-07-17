/*
 * BasicCommand.ino — Basic JARVIS IoT example.
 * 
 * ESP32 connects to WiFi, registers with JARVIS, and responds to:
 *   - "ledon"   → turns LED on
 *   - "ledoff"  → turns LED off
 *   - "toggle"  → toggles LED
 *   - "status"  → returns LED state
 *
 * Circuit: Built-in LED (GPIO 2 on most ESP32 boards)
 */

#include <JarvisIoT.h>

#define LED_PIN 2

bool ledState = false;

// Create JARVIS IoT device
JarvisIoT jarvis(
    "Workshop LED",          // Device name
    "YOUR_WIFI_SSID",        // WiFi SSID
    "YOUR_WIFI_PASSWORD"     // WiFi password
);

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    
    // Initialize WiFi + HTTP server
    jarvis.begin();
    
    // Register commands
    jarvis.onCommand("ledon", [](JsonDocument& p, JsonDocument& r) {
        digitalWrite(LED_PIN, HIGH);
        ledState = true;
        r["status"] = "ok";
        r["data"]["led"] = "on";
        Serial.println("LED ON");
    });
    
    jarvis.onCommand("ledoff", [](JsonDocument& p, JsonDocument& r) {
        digitalWrite(LED_PIN, LOW);
        ledState = false;
        r["status"] = "ok";
        r["data"]["led"] = "off";
        Serial.println("LED OFF");
    });
    
    jarvis.onCommand("toggle", [](JsonDocument& p, JsonDocument& r) {
        ledState = !ledState;
        digitalWrite(LED_PIN, ledState ? HIGH : LOW);
        r["status"] = "ok";
        r["data"]["led"] = ledState ? "on" : "off";
        Serial.printf("LED TOGGLED: %s\n", ledState ? "ON" : "OFF");
    });
    
    jarvis.onCommand("status", [](JsonDocument& p, JsonDocument& r) {
        r["status"] = "ok";
        r["data"]["led"] = ledState ? "on" : "off";
        r["data"]["uptime"] = millis() / 1000;
    });
    
    // Register actuators (what JARVIS can control)
    jarvis.addActuator("led");
    
    // Set metadata
    jarvis.setMetadata("board", "ESP32");
    jarvis.setMetadata("location", "workshop");
    
    // Try to register with JARVIS server
    // (JARVIS must be running on the network)
    if (jarvis.registerWith("192.168.1.100", 8000)) {
        Serial.println("Registered with JARVIS!");
    } else {
        Serial.println("JARVIS not reachable (will retry)");
    }
}

void loop() {
    jarvis.update();
    
    // Re-register every 5 minutes if not registered
    static unsigned long lastRegister = 0;
    if (millis() - lastRegister > 300000) {
        jarvis.registerWith("192.168.1.100", 8000);
        lastRegister = millis();
    }
}
