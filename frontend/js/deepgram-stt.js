class DeepgramSTT {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.socket = null;
        this.mediaRecorder = null;
        this.isRecording = false;
        this.onTranscriptCallback = null;
        this.onFinalCallback = null;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            const url = 'wss://api.deepgram.com/v1/listen?' + new URLSearchParams({
                model: 'nova-2',
                language: 'en',
                punctuate: 'true',
                smart_format: 'true',
                interim_results: 'true',
                endpointing: '300',
                utterance_end_ms: '1000'
            });

            this.socket = new WebSocket(url, ['token', this.apiKey]);

            this.socket.onopen = () => {
                console.log('✅ Deepgram connected');
                resolve();
            };

            this.socket.onmessage = (message) => {
                const data = JSON.parse(message.data);
                
                if (data.type === 'Results') {
                    const transcript = data.channel.alternatives[0].transcript;
                    
                    if (transcript && transcript.trim().length > 0) {
                        const isFinal = data.is_final;
                        
                        if (isFinal && this.onFinalCallback) {
                            this.onFinalCallback(transcript);
                        } else if (this.onTranscriptCallback) {
                            this.onTranscriptCallback(transcript, isFinal);
                        }
                    }
                }
            };

            this.socket.onerror = (error) => {
                console.error('❌ Deepgram error:', error);
                reject(error);
            };

            this.socket.onclose = () => {
                console.log('Deepgram disconnected');
            };
        });
    }

    async startRecording(stream) {
        if (this.isRecording) return;

        await this.connect();

        this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(event.data);
            }
        };

        this.mediaRecorder.start(250);
        this.isRecording = true;
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
        }

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: 'CloseStream' }));
            this.socket.close();
        }
    }

    onTranscript(callback) {
        this.onTranscriptCallback = callback;
    }

    onFinal(callback) {
        this.onFinalCallback = callback;
    }
}
