/**
 * Proctoring Service - Face Detection + Tab Switching
 */

class ProctoringService {
    constructor() {
        this.isActive = false;
        this.faceDetection = null;
        this.camera = null;
        this.videoStream = null;
        this.currentFaceCount = 0;
        this.currentFaceViolation = null; // 'NO_FACE' | 'MULTIPLE_FACES' | null
        
        // Tab switching
        this.tabWarnings = 0;
        this.maxTabWarnings = 5;
        this.lastTabSwitch = 0;
        this.tabSwitchThreshold = 2000; // 2 seconds
        this.lastTabSwitchTime = 0;
        
        // Callbacks
        this.onAutoSubmit = null;
        
        // DOM elements
        this.elements = {};
    }

    init(elements) {
        this.elements = elements;
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isActive) {
                this.handleTabSwitch();
            }
        });

        window.addEventListener('blur', () => {
            if (this.isActive && !document.hidden) {
                this.lastTabSwitchTime = Date.now();
            }
        });

        window.addEventListener('focus', () => {
            if (this.isActive && !document.hidden && this.lastTabSwitchTime) {
                const elapsed = Date.now() - this.lastTabSwitchTime;
                if (elapsed >= this.tabSwitchThreshold) {
                    this.handleTabSwitch();
                }
            }
        });
    }

    async startFaceDetection(videoElement) {
        try {
            // Get the existing stream from the video element if available
            if (videoElement.srcObject) {
                this.videoStream = videoElement.srcObject;
            } else {
                this.videoStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480 }
                });
                videoElement.srcObject = this.videoStream;
            }

            // Check if MediaPipe is available
            if (typeof FaceDetection === 'undefined' || typeof Camera === 'undefined') {
                console.warn('MediaPipe not loaded, skipping face detection');
                return false;
            }

            this.faceDetection = new FaceDetection({
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`;
                }
            });

            this.faceDetection.setOptions({
                model: 'short',
                minDetectionConfidence: 0.5
            });

            this.faceDetection.onResults((results) => this.onFaceResults(results));

            this.camera = new Camera(videoElement, {
                onFrame: async () => {
                    if (this.isActive) {
                        await this.faceDetection.send({ image: videoElement });
                    }
                },
                width: 640,
                height: 480
            });

            await this.camera.start();
            console.log('✅ Face detection started');
            return true;

        } catch (error) {
            console.error('❌ Face detection failed:', error);
            // Don't throw - allow interview to continue without face detection
            return false;
        }
    }

    onFaceResults(results) {
        if (!this.isActive) return;

        const faceCount = results.detections ? results.detections.length : 0;
        this.currentFaceCount = faceCount;

        if (faceCount === 1) {
            this.hideFaceWarning();
        } else if (faceCount === 0) {
            this.showFaceWarning('NO_FACE');
        } else {
            this.showFaceWarning('MULTIPLE_FACES', faceCount);
        }
    }

    showFaceWarning(type, faceCount = 0) {
        if (this.currentFaceViolation === type) return;

        this.currentFaceViolation = type;
        this.setInterviewBlocked(true);

        if (type === 'NO_FACE') {
            if (this.elements.noFaceModal) {
                this.elements.noFaceModal.classList.add('active');
            }
            if (this.elements.modalVideoNoFace && this.videoStream) {
                this.elements.modalVideoNoFace.srcObject = this.videoStream;
            }
            console.log('⚠️ NO FACE WARNING');
        } else if (type === 'MULTIPLE_FACES') {
            if (this.elements.multiFaceModal) {
                this.elements.multiFaceModal.classList.add('active');
            }
            if (this.elements.modalVideoMultiFace && this.videoStream) {
                this.elements.modalVideoMultiFace.srcObject = this.videoStream;
            }
            if (this.elements.detectedFaceCount) {
                this.elements.detectedFaceCount.textContent = faceCount;
            }
            console.log(`⚠️ MULTIPLE FACES: ${faceCount}`);
        }
    }

    hideFaceWarning() {
        if (!this.currentFaceViolation) return;

        console.log('✅ Face issue resolved');

        if (this.elements.noFaceModal) {
            this.elements.noFaceModal.classList.remove('active');
        }
        if (this.elements.multiFaceModal) {
            this.elements.multiFaceModal.classList.remove('active');
        }

        if (this.elements.modalVideoNoFace) {
            this.elements.modalVideoNoFace.srcObject = null;
        }
        if (this.elements.modalVideoMultiFace) {
            this.elements.modalVideoMultiFace.srcObject = null;
        }

        this.currentFaceViolation = null;
        
        // Only unblock if tab modal is not active
        if (!this.elements.tabModal || !this.elements.tabModal.classList.contains('active')) {
            this.setInterviewBlocked(false);
        }
    }

    handleTabSwitch() {
        const now = Date.now();
        if (now - this.lastTabSwitch < this.tabSwitchThreshold) return;

        this.tabWarnings++;
        this.lastTabSwitch = now;

        console.log(`⚠️ Tab switch: ${this.tabWarnings}/${this.maxTabWarnings}`);

        if (this.tabWarnings >= this.maxTabWarnings) {
            console.log('❌ AUTO-SUBMIT');
            this.triggerAutoSubmit();
        } else {
            this.showTabWarning();
        }
    }

    showTabWarning() {
        if (this.elements.tabWarningCount) {
            this.elements.tabWarningCount.textContent = `Warning ${this.tabWarnings}/${this.maxTabWarnings}`;
        }
        if (this.elements.tabRemainingWarnings) {
            this.elements.tabRemainingWarnings.textContent = this.maxTabWarnings - this.tabWarnings;
        }

        if (this.elements.tabModal) {
            this.elements.tabModal.classList.add('active');
        }
        this.setInterviewBlocked(true);
    }

    hideTabWarning() {
        if (this.elements.tabModal) {
            this.elements.tabModal.classList.remove('active');
        }
        
        // Only unblock if face detection is OK
        if (this.currentFaceCount === 1 && !this.currentFaceViolation) {
            this.setInterviewBlocked(false);
        }
    }

    triggerAutoSubmit() {
        this.stop();
        
        if (this.elements.autoSubmitModal) {
            this.elements.autoSubmitModal.classList.add('active');
        }

        if (this.onAutoSubmit) {
            this.onAutoSubmit();
        }
    }

    setInterviewBlocked(blocked) {
        if (this.elements.answerTextarea) {
            this.elements.answerTextarea.disabled = blocked;
        }
        if (this.elements.submitBtn) {
            this.elements.submitBtn.disabled = blocked;
        }
        if (this.elements.skipBtn) {
            this.elements.skipBtn.disabled = blocked;
        }
        if (this.elements.recordBtn) {
            this.elements.recordBtn.disabled = blocked;
        }
    }

    async start(videoElement) {
        this.isActive = true;
        this.tabWarnings = 0;
        this.currentFaceViolation = null;
        this.lastTabSwitch = 0;
        this.lastTabSwitchTime = 0;

        await this.startFaceDetection(videoElement);
        console.log('🎯 Proctoring started');
    }

    stop() {
        this.isActive = false;

        if (this.camera) {
            this.camera.stop();
            this.camera = null;
        }

        // Don't stop the video stream - it's used by the main interview video
        // Only stop face detection tracks if we created a separate stream
        if (this.faceDetection) {
            this.faceDetection.close();
            this.faceDetection = null;
        }

        this.hideFaceWarning();
        if (this.elements.tabModal) {
            this.elements.tabModal.classList.remove('active');
        }

        console.log('⏹️ Proctoring stopped');
    }

    getTabWarnings() {
        return this.tabWarnings;
    }

    isBlocked() {
        return this.currentFaceViolation !== null;
    }
}

window.ProctoringService = ProctoringService;
