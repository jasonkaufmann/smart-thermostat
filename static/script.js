let currentTargetTemp;
let currentSetTemp;
let currentMode;

// Utility function to fetch with a timeout
function fetchWithTimeout(url, options, timeout = 2000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    return fetch(url, {
        ...options,
        signal: controller.signal
    }).finally(() => clearTimeout(id));
}

// Function to check server readiness
function checkServerHealth() {
    console.log("Checking server health");

    fetchWithTimeout("http://10.0.0.54:5000/health", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 2000)
    .then(response => {
        console.log("Received response for server health check");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Server is healthy, initializing desired temperature");
        initializeDesiredTemperature(); // Proceed with initialization
    })
    .catch(error => {
        console.error('Server health check failed, retrying:', error);
        setTimeout(checkServerHealth, 2000); // Retry after 2 seconds
    });
}

// Function to initialize the desired temperature
function initializeDesiredTemperature() {
    console.log("Initializing desired temperature");

    fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 2000)
    .then(response => {
        console.log("Received response for set_temperature");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for set_temperature:", data);
        currentSetTemp = data.desired_temperature;
        currentTargetTemp = currentSetTemp;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
        document.getElementById("desired-temperature").value = currentSetTemp;
    })
    .catch(error => reloadPageIfNeeded(error));
}

// Function to update the time since last action
function updateTimeSinceLastAction() {
    console.log("Updating time since last action");

    fetchWithTimeout("http://10.0.0.54:5000/time_since_last_action", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 2000)
    .then(response => {
        console.log("Received response for time_since_last_action");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for time_since_last_action:", data);
        document.getElementById("time-since-last-action").innerText = data.time_since_last_action + " seconds";
    })
    .catch(error => console.error('Error fetching time since last action:', error));
}

// Function to update the current mode
function updateCurrentMode() {
    console.log("Updating current mode");

    fetchWithTimeout("http://10.0.0.54:5000/current_mode", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 2000)
    .then(response => {
        console.log("Received response for current_mode");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for current_mode:", data);
        document.getElementById("current-mode").innerText = data.current_mode;
        currentMode = data.current_mode.toLowerCase(); // Ensure mode is in lowercase
    })
    .catch(error => console.error('Error fetching current mode:', error));
}

// Function to update the desired temperature
function updateDesiredTemperature() {
    console.log("Updating desired temperature");

    fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 400)
    .then(response => {
        console.log("Received response for set_temperature");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for set_temperature:", data);
        currentSetTemp = data.desired_temperature;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
    })
    .catch(error => console.error('Error fetching desired temperature:', error));
}

// Function to update heat and cool temperature settings
function updateTemperatureSettings() {
    console.log("Updating temperature settings");

    fetchWithTimeout("http://10.0.0.54:5000/temperature_settings", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, 2000)
    .then(response => {
        console.log("Received response for temperature_settings");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for temperature_settings:", data);
        document.getElementById("heat-temperature").innerText = data.current_heat_temp + "°F";
        document.getElementById("cool-temperature").innerText = data.current_cool_temp + "°F";
    })
    .catch(error => console.error('Error fetching temperature settings:', error));
}

// Function to adjust the temperature
function adjustTemperature(change) {
    console.log("Adjusting temperature by", change);
    currentTargetTemp += change;
    document.getElementById("desired-temperature").value = currentTargetTemp;
}

// Function to send the temperature update to the server
function sendTemperatureUpdate() {
    console.log("Sending temperature update to server");
    console.log("Current Set Temp:", currentSetTemp);
    console.log("Current Target Temp:", currentTargetTemp);

    if (currentTargetTemp !== currentSetTemp) {
        fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ temperature: currentTargetTemp })
        }, 400)
        .then(response => {
            console.log("Received response for temperature update");
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => console.log('Temperature update response:', data))
        .catch(error => console.error('Error sending temperature update:', error));
    }
}

// Debounce function to limit the rate of function execution
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// Debounced version of sendTemperatureUpdate to control frequency
const debouncedSendTemperatureUpdate = debounce(sendTemperatureUpdate, 5000);

// Function to activate the light
function activateLight() {
    console.log("Activating light");

    fetchWithTimeout("http://10.0.0.54:5000/activate_light", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    }, 2000)
    .then(response => {
        console.log("Received response for light activation");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => console.log('Light activation response:', data))
    .catch(error => console.error('Error activating light:', error));
}

// Function to reload the page if initial requests fail
function reloadPageIfNeeded(error) {
    console.error('Initial request failed, reloading page:', error);
    setTimeout(() => {
        window.location.reload();
    }, 1000); // Delay for 1 second before reloading
}

// Function to initialize video feed
function initializeVideoFeed() {
    console.log("Initializing video feed");

    setTimeout(() => {
        const video = document.getElementById('video');
        const videoFeedUrl = video.dataset.videoFeedUrl;
        console.log("Video feed URL:", videoFeedUrl);

        // Function to load the next video frame
        function loadNextFrame() {
            video.src = videoFeedUrl + '?t=' + new Date().getTime();
        }

        // Set up the onload event to load the next image
        video.onload = () => {
            console.log("Video frame loaded");
            loadNextFrame(); // Immediately request the next frame after loading the current one
        };

        // Set up the onerror event to handle loading errors
        video.onerror = () => {
            console.error("Failed to load video frame, retrying...");
            setTimeout(loadNextFrame, 1000); // Retry loading the frame after 1 second
        };

        // Load the first frame to start the process
        loadNextFrame();

    }, 5000); // 5-second delay to start video feed
}



// Initialize the desired temperature and update the page every second
window.onload = function() {
    console.log("Window loaded, starting initialization");

    checkServerHealth(); // Start with a server health check

    setInterval(updateTimeSinceLastAction, 1000);
    setInterval(updateCurrentMode, 5000);
    setInterval(updateDesiredTemperature, 5000);
    setInterval(updateTemperatureSettings, 5000); // Update heat and cool settings

    // Add event listeners for temperature buttons
    document.getElementById('increase-temp').addEventListener('click', () => {
        console.log("Increase temperature button clicked");
        adjustTemperature(1);
        debouncedSendTemperatureUpdate();
    });

    document.getElementById('decrease-temp').addEventListener('click', () => {
        console.log("Decrease temperature button clicked");
        adjustTemperature(-1);
        debouncedSendTemperatureUpdate();
    });

    // Add event listener for light button
    document.getElementById('light-btn').addEventListener('click', activateLight);

    initializeVideoFeed(); // Initialize video feed after temperature setup
};
