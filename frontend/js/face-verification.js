/**
 * Face Verification Service
 * Continuously verifies the candidate on camera matches the reference photo.
 * Runs every 3 seconds. Blocks interview if mismatch detected.
 * Pauses automatically when MediaPipe proctoring raises no-face or multi-face warnings.
 */

class FaceVerificationService {
    constructor() {
        this.referenceDescriptor = null;
        this.verificationInterval = null;
        this.isActive = false;
        this.warningActive = false;
        this.DISTANCE_THRESHOLD = 0.54; // match if confidence > 46%
        this.CHECK_INTERVAL_MS = 3000;  // check every 3 seconds
        this.modelsLoaded = false;

        // Rolling window: last 5 checks (= last 15 seconds of data)
        this.ROLLING_WINDOW = 5;
        this.confidenceHistory = [];  // stores last N confidence scores
        this.AVG_THRESHOLD = 45;      // warn only if rolling avg < 45%

        // Elements to block during warning (same pattern as proctoring)
        this.elements = {};
    }

    init(elements) {
        this.elements = elements;
    }

    // ── Model Loading ──────────────────────────────────────────────────────────

    async loadModels() {
        if (this.modelsLoaded) return true;

        // Pin to a specific version to avoid CDN-path issues from "latest" redirects.
        // Must match the library loaded in interview.html (@vladmandic/face-api).
        const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.14/model';

        try {
            console.log('[FaceVerify] Loading face-api.js models from:', MODEL_URL);

            await Promise.all([
                faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL),
                faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
                faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
            ]);

            this.modelsLoaded = true;
            console.log('[FaceVerify] ✅ Models loaded');
            return true;
        } catch (error) {
            console.error('[FaceVerify] ❌ Failed to load models:', error);
            showToast('Face verification models could not be loaded. Proceeding without identity check.', 'warning');
            return false;
        }
    }

    // ── Reference Photo ────────────────────────────────────────────────────────

    async loadReferencePhoto(screeningId) {
        try {
            console.log('[FaceVerify] Loading reference photo for screening:', screeningId);

            const response = await fetch(`/api/screening-results/${screeningId}/reference-photo`);
            if (!response.ok) {
                if (response.status === 404) {
                    console.warn('[FaceVerify] No reference photo on record — face verification disabled');
                    showToast('No reference photo found. Face verification is disabled for this interview.', 'warning');
                } else {
                    console.error('[FaceVerify] Server error fetching reference photo:', response.status);
                    showToast('Could not load reference photo. Face verification disabled.', 'warning');
                }
                return false;
            }

            const blob = await response.blob();
            const img = await this._blobToImage(blob);

            const detection = await faceapi
                .detectSingleFace(img)
                .withFaceLandmarks()
                .withFaceDescriptor();

            if (!detection) {
                console.warn('[FaceVerify] No face detected in reference photo — ensure photo is a clear, front-facing headshot');
                showToast('No face detected in reference photo. Face verification disabled.', 'warning');
                return false;
            }

            this.referenceDescriptor = detection.descriptor;
            console.log('[FaceVerify] ✅ Reference descriptor extracted');
            return true;

        } catch (error) {
            console.error('[FaceVerify] Error loading reference photo:', error);
            return false;
        }
    }

    _blobToImage(blob) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = () => {
                URL.revokeObjectURL(url);
                resolve(img);
            };
            img.onerror = reject;
            img.src = url;
        });
    }

    // ── Start / Stop ───────────────────────────────────────────────────────────

    start() {
        if (!this.referenceDescriptor) {
            console.warn('[FaceVerify] No reference descriptor, not starting');
            return;
        }

        this.isActive = true;
        this.warningActive = false;
        this.confidenceHistory = [];

        // First check immediately, then every 3s
        this._runCheck();
        this.verificationInterval = setInterval(() => {
            this._runCheck();
        }, this.CHECK_INTERVAL_MS);

        console.log('[FaceVerify] ✅ Started (3s interval, rolling avg of last 5 checks)');
    }

    stop() {
        this.isActive = false;
        if (this.verificationInterval) {
            clearInterval(this.verificationInterval);
            this.verificationInterval = null;
        }
        this._hideWarning();
        console.log('[FaceVerify] ⏹️ Stopped');
    }

    // ── Core Verification ──────────────────────────────────────────────────────

    async _runCheck() {
        if (!this.isActive || !this.referenceDescriptor) return;

        // Skip check if MediaPipe proctoring already has an active face warning.
        // If our own warning is active, dismiss it so proctoring takes over cleanly.
        // Reset confidence window so we start fresh after proctoring resolves.
        if (this._isProctoringBlocking()) {
            if (this.warningActive) {
                console.log('[FaceVerify] Proctoring took over - dismissing face-verify warning');
                this._hideWarningForced();
            } else {
                console.log('[FaceVerify] Skipping check - proctoring already blocking');
            }
            this.confidenceHistory = [];
            return;
        }

        const video = document.getElementById('interview-video');
        if (!video || !video.srcObject) return;

        try {
            const detection = await faceapi
                .detectSingleFace(video)
                .withFaceLandmarks()
                .withFaceDescriptor();

            if (!detection) {
                // No face — MediaPipe will handle this, don't double-warn
                return;
            }

            const distance = faceapi.euclideanDistance(
                this.referenceDescriptor,
                detection.descriptor
            );

            const confidence = Math.max(0, Math.min(100, (1 - distance) * 100));

            // Keep only last N readings (sliding window)
            this.confidenceHistory.push(confidence);
            if (this.confidenceHistory.length > this.ROLLING_WINDOW) {
                this.confidenceHistory.shift();
            }

            // Calculate rolling average
            const avgConfidence = this.confidenceHistory.reduce((a, b) => a + b, 0) / this.confidenceHistory.length;
            const isMatch = avgConfidence >= this.AVG_THRESHOLD;

            console.log(`[FaceVerify] Confidence: ${confidence.toFixed(1)}% | Avg(last ${this.confidenceHistory.length}): ${avgConfidence.toFixed(1)}% | Match: ${isMatch}`);

            if (!isMatch && !this.warningActive) {
                this._showWarning(video.srcObject);
            } else if (isMatch && this.warningActive) {
                this._hideWarning();
            }

        } catch (error) {
            // Silent fail — don't disrupt interview on detection errors
            console.warn('[FaceVerify] Detection error (ignored):', error.message);
        }
    }

    // Returns true if MediaPipe proctoring is currently showing no-face or multi-face modal
    _isProctoringBlocking() {
        const noFaceModal = document.getElementById('no-face-modal');
        const multiFaceModal = document.getElementById('multi-face-modal');

        const noFaceActive = noFaceModal && noFaceModal.classList.contains('active');
        const multiFaceActive = multiFaceModal && multiFaceModal.classList.contains('active');

        return noFaceActive || multiFaceActive;
    }

    // ── Warning Modal ──────────────────────────────────────────────────────────

    _showWarning(videoStream) {
        this.warningActive = true;

        const modal = document.getElementById('face-substitution-modal');
        if (modal) {
            modal.classList.add('active');

            // Show live video feed in modal
            const modalVideo = document.getElementById('modal-video-substitution');
            if (modalVideo && videoStream) {
                modalVideo.srcObject = videoStream;
            }
        }

        // Block interview controls
        this._setBlocked(true);
        console.log('[FaceVerify] ⚠️ Warning shown - different person detected');
    }

    _hideWarning() {
        this.warningActive = false;

        const modal = document.getElementById('face-substitution-modal');
        if (modal) {
            modal.classList.remove('active');

            const modalVideo = document.getElementById('modal-video-substitution');
            if (modalVideo) {
                modalVideo.srcObject = null;
            }
        }

        // Only unblock controls if proctoring is also not blocking
        if (!this._isProctoringBlocking()) {
            this._setBlocked(false);
        }

        console.log('[FaceVerify] ✅ Warning cleared - correct person detected');
    }

    // Force-dismiss the face-verify warning without checking proctoring state.
    // Used when proctoring takes over so we don't leave a stale stuck modal.
    _hideWarningForced() {
        this.warningActive = false;

        const modal = document.getElementById('face-substitution-modal');
        if (modal) {
            modal.classList.remove('active');

            const modalVideo = document.getElementById('modal-video-substitution');
            if (modalVideo) {
                modalVideo.srcObject = null;
            }
        }

        // Don't unblock controls here — proctoring is active and will manage that
        console.log('[FaceVerify] ↩️ Warning dismissed - proctoring took over');
    }

    _setBlocked(blocked) {
        const ids = ['answer-textarea', 'record-btn', 'skip-btn'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = blocked;
        });

        // Also block submit button (it's inside answer-actions)
        const submitBtn = document.querySelector('.answer-actions .btn-primary');
        if (submitBtn) submitBtn.disabled = blocked;
    }
}

window.FaceVerificationService = FaceVerificationService;
