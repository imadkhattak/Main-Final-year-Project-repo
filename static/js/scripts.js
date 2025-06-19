document.addEventListener("DOMContentLoaded", function() {
    // Get DOM elements
    const welcomeScreen = document.getElementById("welcome-screen");
    const chatArea = document.getElementById("chat-area");
    const startButton = document.getElementById("start-button");
    const endCallButton = document.getElementById("end-call-button");
    const chatMessages = document.getElementById("chat-messages");
    const statusIndicator = document.getElementById("status-indicator");
    const responseAudio = document.getElementById("response-audio");

    let conversationActive = false; // Track conversation state

    init();

    function init() {
        welcomeScreen.style.display = "flex";
        chatArea.style.display = "none";

        startButton.addEventListener("click", startConversation);
        endCallButton.addEventListener("click", endConversation);

        // These ensure scrollbars are enabled and styled even if you change your CSS
        chatMessages.style.overflowY = "auto";
        chatMessages.style.maxHeight = "70vh";
    }

    async function startConversation() {
        try {
            const initResponse = await fetch('/api/initialize-recorder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-From-Client': 'PeshawarMallAssistant'
                }
            });

            if (!initResponse.ok) throw new Error('Failed to initialize recorder');

            conversationActive = true;
            welcomeScreen.style.display = "none";
            chatArea.style.display = "flex";
            clearMessages();

            const welcomeMessage = "Hello! Welcome to Peshawar Mall Assistant. I'm here to help you find product prices, store locations, and contact information. How can I assist you today?";
            addBotMessage(welcomeMessage);

            // Play TTS and, when done, start listening if conversationActive
            await playTTS(welcomeMessage);

            if (conversationActive) startVoiceInput();

        } catch (error) {
            console.error('Error starting conversation:', error);
            alert('Failed to start conversation. Please try again.');
        }
    }

    async function endConversation() {
        try {
            conversationActive = false;
            await fetch('/api/end-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-From-Client': 'PeshawarMallAssistant'
                }
            });
            chatArea.style.display = "none";
            welcomeScreen.style.display = "flex";
            updateStatus("", "");
        } catch (error) {
            console.error('Error ending conversation:', error);
        }
    }

    async function playTTS(text) {
        try {
            const response = await fetch('/api/text-to-speech', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-From-Client': 'PeshawarMallAssistant'
                },
                body: JSON.stringify({ text, voice: 'en-US-AriaNeural' })
            });

            if (!response.ok) throw new Error('TTS request failed');

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            return new Promise((resolve, reject) => {
                responseAudio.src = audioUrl;
                responseAudio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    resolve();
                };
                responseAudio.onerror = reject;
                responseAudio.play().catch(reject);
            });
        } catch (error) {
            console.error('Error playing TTS:', error);
        }
    }

    async function startVoiceInput() {
        if (!conversationActive) return;

        try {
            updateStatus("listening", "Listening... Please speak now");

            // Start VAD-based recording on backend
            const response = await fetch('/api/start-vad-recording', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-From-Client': 'PeshawarMallAssistant'
                },
                body: JSON.stringify({
                    max_duration: 15,
                    silence_timeout: 4
                })
            });

            updateStatus("processing", "Processing your request...");

            const data = await response.json();

            if (!data.success || !data.transcript) {
                addBotMessage("Sorry, I could not hear you. Please try again.");
                updateStatus("listening", "Listening... Please speak now");
                if (conversationActive) setTimeout(startVoiceInput, 1000);
                return;
            }

            addUserMessage(data.transcript);
            updateStatus("processing", "Processing your request...");

            // Send transcript to chat API
            const chatResp = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-From-Client': 'PeshawarMallAssistant'
                },
                body: JSON.stringify({ message: data.transcript })
            });
            const chatData = await chatResp.json();

            if (!chatData.success || !chatData.response) {
                addBotMessage("Sorry, I couldn't process your query.");
                updateStatus("listening", "Listening... Please speak now");
                if (conversationActive) setTimeout(startVoiceInput, 1000);
                return;
            }

            addBotMessage(chatData.response);
            await playTTS(chatData.response);

            // If bot says conversation is over, stop everything
            if (isConversationEnd(chatData.response)) {
                conversationActive = false;
                updateStatus("ended", "Conversation ended.");
                await fetch('/api/end-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-From-Client': 'PeshawarMallAssistant'
                    }
                });
                return;
            }

            // Ready for next input: immediately listen again if still active
            if (conversationActive) {
                updateStatus("listening", "Listening... Please speak now");
                setTimeout(startVoiceInput, 500);
            }

        } catch (e) {
            addBotMessage("Error receiving or processing your request. Please try again.");
            updateStatus("listening", "Listening... Please speak now");
            if (conversationActive) setTimeout(startVoiceInput, 1500);
        }
    }

    // Utility functions below

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${isUser ? "user-message" : "bot-message"}`;
        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        messageContent.textContent = content;
        const timestamp = document.createElement("div");
        timestamp.className = "timestamp";
        timestamp.textContent = getCurrentTime();
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(timestamp);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function addBotMessage(content) {
        addMessage(content, false);
    }

    function addUserMessage(content) {
        addMessage(content, true);
    }

    function clearMessages() {
        chatMessages.innerHTML = "";
    }

    function scrollToBottom() {
        // Always scroll to the bottom (latest message)
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }

    function updateStatus(statusClass, statusText) {
        statusIndicator.className = `status-indicator ${statusClass}`;
        statusIndicator.textContent = statusText;
    }

    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function isConversationEnd(text) {
        const endPhrases = [
            "goodbye",
            "thank you for visiting",
            "have a great day",
            "see you again",
            "conversation ended",
            "session ended",
            "thanks for coming",
            "thank you for coming",
            "bye",
            "thank you, goodbye"
        ];
        const lower = text.toLowerCase();
        return endPhrases.some(phrase => lower.includes(phrase));
    }

    window.addEventListener("resize", () => {
        if (chatArea.style.display !== "none") {
            scrollToBottom();
        }
    });
});