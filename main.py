<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Thermostat</title>
    <script>
        // Function to update the time since last action
        function updateTimeSinceLastAction() {
            fetch("/time_since_last_action")
                .then(response => response.json())
                .then(data => {
                    document.getElementById("time-since-last-action").innerText = data.time_since_last_action + " seconds";
                });
        }

        // Function to update the ambient temperature
        function updateAmbientTemperature() {
            fetch("/ambient_temperature")
                .then(response => response.json())
                .then(data => {
                    document.getElementById("ambient-temperature").innerText = data.ambient_temperature.toFixed(1) + "°F";
                });
        }

        // Update the time and temperature every second
        setInterval(updateTimeSinceLastAction, 1000);
        setInterval(updateAmbientTemperature, 1000);
    </script>
</head>
<body>
    <h1>Smart Thermostat Control</h1>
    <form method="POST">
        <label for="temperature">Desired Temperature:</label>
        <input type="number" id="temperature" name="temperature" value="{{ current_heat_temp }}" min="60" max="90">
        <button type="submit" name="set_temperature">Set Temperature</button>

        <div>
            <label>Mode:</label>
            {% for mode in mode_options %}
            <label>
                <input type="radio" name="mode" value="{{ mode.lower() }}" {% if current_mode == loop.index0 %}checked{% endif %}>
                {{ mode }}
            </label>
            {% endfor %}
        </div>

        <button type="submit" name="light">Light</button>

        <!-- Button to toggle manual mode -->
        <button type="submit" name="manual_override">
            {{ 'Disable' if manual_override else 'Enable' }} Manual Mode
        </button>
    </form>
    <p>Current Heat Temperature: {{ current_heat_temp }}°F</p>
    <p>Current Cool Temperature: {{ current_cool_temp }}°F</p>
    <p>Ambient Temperature: <span id="ambient-temperature">{{ ambient_temp | round(1) }}°F</span></p>
    <p>Current Mode: {{ mode_options[current_mode] }}</p>
    <p>Manual Override: {{ 'Active' if manual_override else 'Inactive' }}</p>
    <p>Time Since Last Action: <span id="time-since-last-action">{{ time_since_last_action | round(1) }} seconds</span></p>
</body>
</html>
