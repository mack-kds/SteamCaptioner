/**
 * StreamCaptioner Web Client
 * Real-time caption display with accessibility features
 */

class CaptionClient {
    constructor() {
        this.ws = null;
        this.currentFeed = null;
        this.captions = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.isAtBottom = true;  // Track if user is viewing live
        this.interimElement = null;  // Track interim caption element
        this.loadingHistory = false;  // Track if loading history
        this.historyLoaded = false;  // Track if history already loaded for current feed
        this.captionIds = new Set();  // Track caption IDs to prevent duplicates

        // Default settings
        this.defaultSettings = {
            fontFamily: 'system-ui, sans-serif',
            fontSize: 32,
            textColor: '#ffffff',
            bgColor: '#000000',
            highContrast: false,
            showInterim: true,
            showTimestamps: false
        };

        this.settings = this.loadSettings();
        this.init();
    }
    
    async init() {
        await this.loadFeeds();
        this.applySettings();
        this.setupEventListeners();
    }
    
    async loadFeeds() {
        try {
            const response = await fetch('/api/feeds');
            const data = await response.json();
            this.populateFeedSelector(data.feeds || []);
            
            if (data.feeds && data.feeds.length > 0) {
                this.connectToFeed(data.feeds[0].id);
            }
        } catch (error) {
            console.error('Failed to load feeds:', error);
            this.setStatus('Error loading feeds', 'disconnected');
        }
    }
    
    populateFeedSelector(feeds) {
        const selector = document.getElementById('feed-selector');
        selector.innerHTML = '';
        
        if (feeds.length === 0) {
            selector.innerHTML = '<option value="">No feeds available</option>';
            return;
        }
        
        feeds.forEach(feed => {
            const option = document.createElement('option');
            option.value = feed.id;
            option.textContent = feed.name;
            selector.appendChild(option);
        });
    }
    
    connectToFeed(feedId, isReconnect = false) {
        // Close existing connection
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        // Clear captions when switching feeds (not on reconnect to same feed)
        if (!isReconnect) {
            console.log('Switching to feed:', feedId, '- clearing captions');
            this.captions = [];
            this.captionIds = new Set();
            this.interimElement = null;
            this.loadingHistory = false;
            this.historyLoaded = false;
            const container = document.getElementById('caption-scroll');
            if (container) {
                container.innerHTML = '';
            }
            // Reset scroll position
            const scrollContainer = document.getElementById('caption-container');
            if (scrollContainer) {
                scrollContainer.scrollTop = 0;
            }
            this.isAtBottom = true;
        }

        this.currentFeed = feedId;
        this.setStatus('Connecting...', 'connecting');
        
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws/${feedId}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.setStatus('Connected', 'connected');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                // Handle ping/pong first (plain text)
                if (event.data === 'ping') {
                    this.ws.send('pong');
                    return;
                }
                if (event.data === 'pong') {
                    return;
                }

                try {
                    const data = JSON.parse(event.data);

                    // Handle history markers
                    if (data.type === 'history_start') {
                        // Skip history if already loaded (reconnect scenario)
                        if (this.historyLoaded) {
                            console.log('Skipping history - already loaded');
                            this.loadingHistory = true;  // Set flag to skip incoming history items
                        } else {
                            this.loadingHistory = true;
                        }
                        return;
                    }
                    if (data.type === 'history_end') {
                        this.loadingHistory = false;
                        this.historyLoaded = true;
                        // Scroll to bottom after history loads
                        const scrollContainer = document.getElementById('caption-container');
                        if (scrollContainer) {
                            scrollContainer.scrollTop = scrollContainer.scrollHeight;
                        }
                        return;
                    }

                    // Handle caption data - skip if already have this caption
                    if (data.text !== undefined) {
                        // Create unique ID from timestamp and text
                        const captionId = `${data.timestamp}-${data.text}`;

                        // Skip if we already have this caption (duplicate from reconnect)
                        if (this.captionIds.has(captionId)) {
                            return;
                        }

                        // Skip history items if history already loaded
                        if (this.loadingHistory && this.historyLoaded) {
                            return;
                        }

                        this.captionIds.add(captionId);
                        this.handleCaption(data, this.loadingHistory);
                    }
                } catch (e) {
                    console.debug('WebSocket message parse error:', e);
                }
            };
            
            this.ws.onclose = () => {
                this.setStatus('Disconnected', 'disconnected');
                this.scheduleReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.setStatus('Connection error', 'disconnected');
            };
        } catch (error) {
            console.error('Failed to connect:', error);
            this.setStatus('Connection failed', 'disconnected');
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts && this.currentFeed) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5);
            setTimeout(() => this.connectToFeed(this.currentFeed, true), delay);
        }
    }
    
    handleCaption(caption, isHistory = false) {
        const container = document.getElementById('caption-scroll');
        const scrollContainer = container.parentElement;

        // Check if we should show interim results (skip interim for history)
        if (!caption.is_final && (!this.settings.showInterim || isHistory)) {
            return;
        }

        if (caption.is_final && caption.text) {
            // Remove interim element if exists (not during history load)
            if (this.interimElement && !isHistory) {
                this.interimElement.remove();
                this.interimElement = null;
            }

            // Create new caption line
            const line = document.createElement('div');
            line.className = 'caption-line';

            // Don't animate history items
            if (isHistory) {
                line.style.animation = 'none';
            }

            if (this.settings.showTimestamps && caption.timestamp) {
                const time = document.createElement('span');
                time.className = 'caption-time';
                const captionTime = caption.timestamp ? new Date(caption.timestamp * 1000) : new Date();
                time.textContent = captionTime.toLocaleTimeString();
                line.appendChild(time);
            }

            const text = document.createTextNode(caption.text);
            line.appendChild(text);

            // Always append at bottom (newest at bottom, scroll down to follow)
            container.appendChild(line);

            // Store caption
            this.captions.push({
                ...caption,
                receivedAt: new Date()
            });

            // Keep only last 200 captions
            if (this.captions.length > 200) {
                this.captions.shift();
                // Remove oldest DOM element (first child)
                if (container.firstChild) {
                    container.firstChild.remove();
                }
            }

            // Auto-scroll to bottom if user is viewing live (not during history load)
            if (this.isAtBottom && !isHistory) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        } else if (!caption.is_final && caption.text) {
            // Update or create interim element (always at bottom)
            if (!this.interimElement) {
                this.interimElement = document.createElement('div');
                this.interimElement.className = 'caption-line interim';
                container.appendChild(this.interimElement);
            }
            this.interimElement.textContent = caption.text;

            // Auto-scroll to bottom if user is viewing live
            if (this.isAtBottom) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }
    
    setStatus(text, state) {
        const status = document.getElementById('connection-status');
        status.textContent = text;
        status.className = `status-${state}`;
    }
    
    loadSettings() {
        try {
            const saved = localStorage.getItem('captionSettings');
            return saved ? { ...this.defaultSettings, ...JSON.parse(saved) } : { ...this.defaultSettings };
        } catch (e) {
            return { ...this.defaultSettings };
        }
    }
    
    saveSettings() {
        localStorage.setItem('captionSettings', JSON.stringify(this.settings));
    }

    applySettings() {
        const root = document.documentElement;
        root.style.setProperty('--font-family', this.settings.fontFamily);
        root.style.setProperty('--font-size', `${this.settings.fontSize}px`);
        root.style.setProperty('--text-color', this.settings.textColor);
        root.style.setProperty('--bg-color', this.settings.bgColor);
        document.body.classList.toggle('high-contrast', this.settings.highContrast);

        // Update form controls
        document.getElementById('font-family').value = this.settings.fontFamily;
        document.getElementById('font-size').value = this.settings.fontSize;
        document.getElementById('font-size-value').textContent = `${this.settings.fontSize}px`;
        document.getElementById('text-color').value = this.settings.textColor;
        document.getElementById('bg-color').value = this.settings.bgColor;
        document.getElementById('high-contrast').checked = this.settings.highContrast;
        document.getElementById('show-interim').checked = this.settings.showInterim;
    }

    setupEventListeners() {
        // Feed selector
        document.getElementById('feed-selector').addEventListener('change', (e) => {
            if (e.target.value) {
                this.connectToFeed(e.target.value);
            }
        });

        // Settings panel toggle
        document.getElementById('settings-btn').addEventListener('click', () => {
            document.getElementById('settings-panel').classList.remove('hidden');
            document.getElementById('overlay').classList.remove('hidden');
        });

        document.getElementById('close-settings').addEventListener('click', () => {
            this.closeSettings();
        });

        document.getElementById('overlay').addEventListener('click', () => {
            this.closeSettings();
        });

        // Settings controls
        document.getElementById('font-family').addEventListener('change', (e) => {
            this.settings.fontFamily = e.target.value;
            this.applySettings();
            this.saveSettings();
        });

        document.getElementById('font-size').addEventListener('input', (e) => {
            this.settings.fontSize = parseInt(e.target.value);
            document.getElementById('font-size-value').textContent = `${this.settings.fontSize}px`;
            this.applySettings();
            this.saveSettings();
        });

        document.getElementById('text-color').addEventListener('input', (e) => {
            this.settings.textColor = e.target.value;
            this.applySettings();
            this.saveSettings();
        });

        document.getElementById('bg-color').addEventListener('input', (e) => {
            this.settings.bgColor = e.target.value;
            this.applySettings();
            this.saveSettings();
        });

        document.getElementById('high-contrast').addEventListener('change', (e) => {
            this.settings.highContrast = e.target.checked;
            this.applySettings();
            this.saveSettings();
        });

        document.getElementById('show-interim').addEventListener('change', (e) => {
            this.settings.showInterim = e.target.checked;
            this.saveSettings();
        });

        document.getElementById('reset-settings').addEventListener('click', () => {
            this.settings = { ...this.defaultSettings };
            this.applySettings();
            this.saveSettings();
        });

        // Scroll detection for "Return to Live" button
        const captionContainer = document.getElementById('caption-container');
        const returnBtn = document.getElementById('return-to-live');
        let scrollTimeout = null;

        captionContainer.addEventListener('scroll', () => {
            // Debounce scroll detection to avoid flickering
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }

            scrollTimeout = setTimeout(() => {
                // Check if scrolled away from bottom (since newest is at bottom)
                const scrollTop = captionContainer.scrollTop;
                const scrollHeight = captionContainer.scrollHeight;
                const clientHeight = captionContainer.clientHeight;
                const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

                this.isAtBottom = distanceFromBottom < 100;  // Within 100px of bottom = "live"

                if (this.isAtBottom) {
                    returnBtn.classList.add('hidden');
                } else {
                    returnBtn.classList.remove('hidden');
                }
            }, 50);  // 50ms debounce
        });

        // Return to live button
        returnBtn.addEventListener('click', () => {
            captionContainer.scrollTop = captionContainer.scrollHeight;
            this.isAtBottom = true;
            returnBtn.classList.add('hidden');
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSettings();
            }
            if (e.key === '+' || e.key === '=') {
                this.settings.fontSize = Math.min(96, this.settings.fontSize + 4);
                this.applySettings();
                this.saveSettings();
            }
            if (e.key === '-') {
                this.settings.fontSize = Math.max(16, this.settings.fontSize - 4);
                this.applySettings();
                this.saveSettings();
            }
        });
    }

    closeSettings() {
        document.getElementById('settings-panel').classList.add('hidden');
        document.getElementById('overlay').classList.add('hidden');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.captionClient = new CaptionClient();
});

