const helpKeywords = ['help', 'issue', 'support', 'assistance', 'problem'];
const fallbackReplies = [
    "I'm sorry, I didn't understand that. Can you please rephrase?",
    "Okay, please describe your issue."
];

// Category structure
const issueCategories = {
    'Server': {
        categories: {
            'Access Issues': {
                issues: {
                    'Login': {
                        subIssues: ['URL not working', 'Connection timed out']
                    },
                    'Forgot password': {},
                    'The page is unresponsive': {}
                }
            },
            'Reports & Tracking': {
                issues: {
                    'Track and Trace': {},
                    'Scheduled Report': {}
                    
                }
            },
            'Inventory': {
                issues: {
                    'Picklists': {},
                    'Empty Locations': {},
                    'Top Locations': {}
                }
            }
        },
        issues: {
            'Others': {},
            'Email Us': { isAction: true }
        }
    },
    'Adapter': {
        categories: {
            'Connection Issues': {
                issues: {
                    'Adapter not launching': {},
                    'Reader disconnected': {},
                    'Reader lights issue': {}
                }
            }
        },
        issues: {
            'Others': {},
            'Email Us': { isAction: true }
        }
    },
    'AGM': {
        categories: {
            'Connectivity Issues': {
                issues: {
                    'Cannot connect to server': {},
                    'Device name or URL issue': {},
                    'Wrong username/password': {},
                    'Integrity not verified': {}
                }
            },
            'Scanning Issues': {
                issues: {
                    'RFID/Barcode not scanning': {},
                    'RFID/Barcode field not filling': {}
                }
            }
        },
        issues: {
            'Others': {},
            'Email Us': { isAction: true }
        }
    }
};

// Main functions
function sendMessage() {
    const userInput = document.getElementById('userInput').value.trim();
    if (userInput === '') return;

    appendUserMessage(userInput);

    const lowerInput = userInput.toLowerCase();
    const trimmedInput = lowerInput.trim();

    // ✅ Only trigger help menu if user types exactly a help keyword
      const helpTriggers = ['issue', 'support', 'help', 'problem', 'assistance'];
if (helpTriggers.includes(trimmedInput)) {
    // ✅ REMOVED: document.getElementById('chatBox').innerHTML = ''; (NO CLEARING!)
    appendBotMessage("Please choose the software you need assistance with:");
    renderButtons(['Server', 'Adapter', 'AGM'], 'software-button', (software) => {
        sendQuickOption(software);
    });
    document.getElementById('userInput').value = ''; // Clear input field only
    return;
}

    // 🔁 Otherwise, send to backend as normal
    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userInput })
    })
    .then(response => response.json())
    .then(data => {
        typeResponse(data.response, document.getElementById('chatBox'));
    })
    .catch(error => {
        console.error('Error:', error);
    });

    document.getElementById('userInput').value = '';
}

function sendQuickOption(option, buttonElement = null) {
    if (buttonElement) markButtonClicked(buttonElement);
    
    if (['Server', 'Adapter', 'AGM'].includes(option)) {
        showCategoryButtons(option);
        return;
    }

    if (option === 'Others') {
        appendBotMessage(`
            <div class="others-message">
                <p>Okay, please describe your issue.</p>
                <p>If you need further help, you can <span class="email-link" onclick="openEmailPopup()">email our support team</span>.</p>
            </div>
        `);
        return;
    }

    if (option === 'Email Us') {
        openEmailPopup();
        return;
    }

    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: option })
    })
    .then(response => response.json())
    .then(data => {
        typeResponse(data.response, document.getElementById('chatBox'));
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// UI Rendering
function showMainMenu() {
    const chatBox = document.getElementById('chatBox');
    // Clear any existing buttons
    const existingButtons = chatBox.querySelectorAll('.button-container');
    existingButtons.forEach(btn => btn.remove());
    
    renderButtons(['Server', 'Adapter', 'AGM'], 'software-button', (software) => {
        sendQuickOption(software);
    });
}

function showCategoryButtons(software) {
    appendBotMessage(`Great! Let's get started with ${software} troubleshooting:`);
    
    const categories = issueCategories[software];
    const buttons = [];
    
    for (const [category, data] of Object.entries(categories.categories)) {
        buttons.push({
            text: category,
            onClick: () => showIssueButtons(software, category)
        });
    }
    
    for (const [issue, data] of Object.entries(categories.issues)) {
        buttons.push({
            text: issue,
            onClick: () => data.isAction ? openEmailPopup() : sendQuickOption(issue)
        });
    }
    
    renderButtons(buttons.map(b => b.text), 'category-button', (_, index) => {
        buttons[index].onClick();
    });
}

function showIssueButtons(software, category) {
    const issues = issueCategories[software].categories[category].issues;
    const buttons = [];
    
    for (const [issue, data] of Object.entries(issues)) {
        buttons.push({
            text: issue,
            onClick: data.subIssues ? 
                () => showSubIssues(software, category, issue, data.subIssues) : 
                () => sendQuickOption(issue)
        });
    }
    
    renderButtons(buttons.map(b => b.text), 'issue-button', (_, index) => {
        buttons[index].onClick();
    });
}

function showSubIssues(software, category, issue, subIssues) {
    renderButtons(subIssues, 'subissue-button', (subIssue) => {
        sendQuickOption(subIssue);
    });
}

function renderButtons(buttonTexts, buttonClass, onClick) {
    const chatBox = document.getElementById('chatBox');
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';
    
    buttonTexts.forEach((text, index) => {
        const button = document.createElement('button');
        button.className = `round-button ${buttonClass}`;
        button.textContent = text;
        button.onclick = () => {
            document.querySelectorAll(`.${buttonClass}`).forEach(btn => {
                btn.classList.remove('clicked');
            });
            button.classList.add('clicked');
            onClick(text, index);
        };
        buttonContainer.appendChild(button);
    });
    
    chatBox.appendChild(buttonContainer);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Helper functions
function appendUserMessage(text) {
    const chatBox = document.getElementById('chatBox');
    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = text;
    chatBox.appendChild(userMessage);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendBotMessage(text) {
    const chatBox = document.getElementById('chatBox');
    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message';
    botMessage.innerHTML = text;
    chatBox.appendChild(botMessage);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function markButtonClicked(button) {
    const buttons = document.querySelectorAll('.round-button');
    buttons.forEach(btn => btn.classList.remove('clicked'));
    button.classList.add('clicked');
}

function typeResponse(responseText, chatBox) {
    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message';
    chatBox.appendChild(botMessage);

    let normalizedText = responseText
        .replace(/\n/g, '<br>')
        .replace(/\[x\]/g, '✅')
        .replace(/\[ \]/g, '⬜');

    let index = 0;
    botMessage.innerHTML = '';

    function type() {
        if (index < normalizedText.length) {
            const char = normalizedText.charAt(index);
            if (normalizedText.substr(index, 4) === '<br>') {
                botMessage.innerHTML += '<br>';
                index += 4;
            } else {
                botMessage.innerHTML += char;
                index++;
            }
            setTimeout(type, 20);
        } else {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
    setTimeout(type, 400);
}

// Email functions
function openEmailPopup() {
    document.getElementById("emailPopup").style.display = "block";
}

function closeEmailPopup() {
    document.getElementById("emailPopup").style.display = "none";
}

function sendEmail() {
    const name = document.getElementById("emailName").value.trim();
    const from = document.getElementById("emailFrom").value.trim();
    const message = document.getElementById("emailMessage").value.trim();

    if (!name || !from || !message) {
        alert("⚠️ Please fill in all fields.");
        return;
    }

    const subject = encodeURIComponent("Support Request via APBot");
    const body = encodeURIComponent(
        `Hi Team,\n\nMy name is ${name}.\nEmail: ${from}\n\nIssue:\n${message}\n\nThanks,\n${name}`
    );

    const mailtoLink = `mailto:team@assetpulse.com?subject=${subject}&body=${body}`;
    window.open(mailtoLink, '_blank');
    closeEmailPopup();
}

// Utility
function handleKeyPress(event) {
    if (event.key === "Enter") sendMessage();
}

// Initial welcome message
document.addEventListener('DOMContentLoaded', function () {
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';
    appendBotMessage("Hello! How can I assist you today?");
    
    setTimeout(() => {
        appendBotMessage("Please choose the software you need assistance with ot type Issue:");
        renderButtons(['Server', 'Adapter', 'AGM'], 'software-button', (software) => {
            sendQuickOption(software);
        });
    }, 500);
});