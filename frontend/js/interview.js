let interviewId;
let currentQuestionIndex = 0;
let questions = [];
let completeVideoRecorder;
let completeVideoChunks = [];
let deepgramSTT;
let currentAnswerTranscript = '';
let finalTranscripts = [];
let timerInterval;
let totalTimeRemaining = 1500; // 25 minutes in seconds
let isMicMuted = false;
let isVideoOff = false;
let proctoringService = null;
let isAutoSubmitted = false;
let faceVerificationService = null;

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    interviewId = urlParams.get('id');
    
    if (!interviewId) {
        showToast('Invalid interview session', 'error');
        setTimeout(() => window.location.href = '/candidate.html', 2000);
        return;
    }
    
    try {
        // Initialize proctoring
        proctoringService = new ProctoringService();
        proctoringService.init({
            noFaceModal: document.getElementById('no-face-modal'),
            multiFaceModal: document.getElementById('multi-face-modal'),
            tabModal: document.getElementById('tab-switch-modal'),
            autoSubmitModal: document.getElementById('auto-submit-modal'),
            modalVideoNoFace: document.getElementById('modal-video-no-face'),
            modalVideoMultiFace: document.getElementById('modal-video-multi-face'),
            detectedFaceCount: document.getElementById('detected-face-count'),
            tabWarningCount: document.getElementById('tab-warning-count'),
            tabRemainingWarnings: document.getElementById('tab-remaining-warnings'),
            answerTextarea: document.getElementById('answer-textarea'),
            submitBtn: document.querySelector('.answer-actions .btn-primary'),
            skipBtn: document.getElementById('skip-btn'),
            recordBtn: document.getElementById('record-btn')
        });
        
        proctoringService.onAutoSubmit = handleAutoSubmit;
        
        // Tab understand button handler
        const tabUnderstandBtn = document.getElementById('tab-understand-btn');
        if (tabUnderstandBtn) {
            tabUnderstandBtn.addEventListener('click', () => {
                if (proctoringService) {
                    proctoringService.hideTabWarning();
                }
            });
        }
        
        // Show proctoring rules modal
        showProctoringRulesModal();
        
    } catch (error) {
        console.error('Initialization error:', error);
        showToast('Failed to initialize interview', 'error');
    }
    
    const config = await apiCall('/config/deepgram-key');
    deepgramSTT = new DeepgramSTT(config.api_key);
    
    deepgramSTT.onTranscript((transcript, isFinal) => {
        displayLiveTranscript(transcript, isFinal);
    });
    
    deepgramSTT.onFinal((transcript) => {
        finalTranscripts.push(transcript);
        currentAnswerTranscript = finalTranscripts.join(' ');
        window.tempInterimValue = currentAnswerTranscript;
    });
});

// Show proctoring rules modal
function showProctoringRulesModal() {
    const modal = document.getElementById('proctoring-rules-modal');
    const agreeBtn = document.getElementById('agree-rules-btn');
    
    if (!modal || !agreeBtn) {
        // If modal doesn't exist, start interview directly
        initializeInterview();
        return;
    }
    
    modal.classList.add('active');
    
    agreeBtn.onclick = async () => {
        modal.classList.remove('active');
        await initializeInterview();
    };
}

// Setup copy-paste blocking
function setupCopyPasteBlocking() {
    const textarea = document.getElementById('answer-textarea');
    
    if (!textarea) return;
    
    textarea.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showToast('Right-click is disabled', 'warning');
    });
    
    textarea.addEventListener('copy', (e) => {
        e.preventDefault();
        showToast('Copy is disabled', 'warning');
    });
    
    textarea.addEventListener('cut', (e) => {
        e.preventDefault();
        showToast('Cut is disabled', 'warning');
    });
    
    textarea.addEventListener('paste', (e) => {
        e.preventDefault();
        showToast('Paste is disabled', 'warning');
    });
    
    textarea.addEventListener('keydown', (e) => {
        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        const cmdKey = isMac ? e.metaKey : e.ctrlKey;
        
        if (cmdKey && ['c', 'v', 'x'].includes(e.key.toLowerCase())) {
            e.preventDefault();
            showToast('Keyboard shortcuts are disabled', 'warning');
        }
    });
}

// Handle auto-submit
async function handleAutoSubmit() {
    isAutoSubmitted = true;
    
    // Stop timer and recording
    stopTotalTimer();
    if (deepgramSTT && deepgramSTT.isRecording) {
        deepgramSTT.stopRecording();
    }
    
    try {
        // Stop video recording
        if (completeVideoRecorder && completeVideoRecorder.state === 'recording') {
            completeVideoRecorder.stop();
            
            // Wait for the onstop event
            await new Promise(resolve => {
                completeVideoRecorder.onstop = () => {
                    console.log('Video recorder stopped. Total chunks:', completeVideoChunks.length);
                    setTimeout(resolve, 500);
                };
            });
        }
        
        // Mark interview as complete with auto-submit flags first
        await apiCall(`/interviews/${interviewId}/complete`, {
            method: 'POST',
            body: JSON.stringify({
                auto_submitted: true,
                auto_submit_reason: 'multiple_tab_switches'
            })
        });
        
        // Update modal to show upload status
        updateAutoSubmitModal('uploading');
        
        // Upload video if we have chunks
        if (completeVideoChunks.length > 0) {
            const videoBlob = new Blob(completeVideoChunks, { 
                type: 'video/webm;codecs=vp9,opus' 
            });
            
            if (videoBlob.size > 0) {
                await uploadCompleteVideo(videoBlob);
            }
        }
        
        // Update modal to show completion
        updateAutoSubmitModal('completed');
        
        // Redirect after 3 seconds
        setTimeout(() => {
            window.location.href = '/candidate.html?completed=true&auto_submitted=true';
        }, 3000);
        
    } catch (error) {
        console.error('Auto-submit error:', error);
        showToast('Error during auto-submit', 'error');
        
        // Still redirect even if upload fails
        setTimeout(() => {
            window.location.href = '/candidate.html?completed=true&auto_submitted=true';
        }, 3000);
    }
}

// Update auto-submit modal status
function updateAutoSubmitModal(status) {
    const icon = document.getElementById('auto-submit-icon');
    const title = document.getElementById('auto-submit-title');
    const message = document.getElementById('auto-submit-message');
    const uploadStatus = document.getElementById('upload-status');
    const completionStatus = document.getElementById('completion-status');
    
    if (!icon || !title || !message || !uploadStatus || !completionStatus) {
        console.warn('Auto-submit modal elements not found');
        return;
    }
    
    if (status === 'uploading') {
        // Hide initial message
        message.style.display = 'none';
        
        // Show upload status
        uploadStatus.style.display = 'block';
        completionStatus.style.display = 'none';
        
    } else if (status === 'completed') {
        // Hide upload status
        uploadStatus.style.display = 'none';
        
        // Update title and icon
        icon.textContent = '✓';
        icon.style.color = '#28a745';
        icon.style.fontSize = '80px';
        title.textContent = 'Upload Complete';
        
        // Show completion status
        completionStatus.style.display = 'block';
    }
}

async function initializeInterview() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720, frameRate: 30 },
            audio: { 
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 48000
            }
        });
        
        const video = document.getElementById('interview-video');
        video.srcObject = stream;
        
        startCompleteVideoRecording(stream);
        
        const response = await apiCall(`/interviews/${interviewId}/start`, {
            method: 'POST'
        });
        
        questions = response.questions || [];
        
        // Debug: Log the structure of questions
        console.log('=== QUESTIONS DEBUG ===');
        console.log('Total questions:', questions.length);
        if (questions.length > 0) {
            console.log('First question structure:', JSON.stringify(questions[0], null, 2));
            console.log('First question type:', typeof questions[0]);
            if (typeof questions[0] === 'object') {
                console.log('First question.text type:', typeof questions[0].text);
                console.log('First question.text value:', questions[0].text);
            }
        }
        console.log('======================');
        
        if (questions.length === 0) {
            showToast('No questions available for this interview', 'error');
            console.error('Empty questions array in response:', response);
            return;
        }
        
        document.getElementById('total-questions').textContent = questions.length;
        
        showQuestion(0);
        
        // Setup copy-paste blocking
        setupCopyPasteBlocking();
        
        // Start proctoring
        if (proctoringService) {
            await proctoringService.start(video);
        }

        // Start total interview timer (25 minutes)
        startTotalTimer();

        // Start face verification in background — must not block the interview start
        initializeFaceVerification();
        
    } catch (error) {
        console.error('Initialize error:', error);
        showToast('Failed to start interview: ' + error.message, 'error');
    }
}

function startCompleteVideoRecording(stream) {
    completeVideoChunks = [];
    
    const options = {
        mimeType: 'video/webm;codecs=vp9,opus',
        videoBitsPerSecond: 2500000
    };
    
    // Check if browser supports the mime type
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        console.warn('vp9 not supported, trying vp8');
        options.mimeType = 'video/webm;codecs=vp8,opus';
    }
    
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        console.warn('vp8 not supported, using default');
        options.mimeType = 'video/webm';
    }
    
    completeVideoRecorder = new MediaRecorder(stream, options);
    
    completeVideoRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
            console.log('Video data received:', event.data.size, 'bytes');
            completeVideoChunks.push(event.data);
        }
    };
    
    completeVideoRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
    };
    
    // Start recording - will collect all data when stopped
    completeVideoRecorder.start();
    console.log('Video recording started with mime type:', options.mimeType);
    
    document.getElementById('recording-indicator').style.display = 'flex';
}

function showQuestion(index) {
    currentQuestionIndex = index;
    const question = questions[index];
    
    if (!question) {
        console.error('Question not found at index:', index);
        showToast('Error loading question', 'error');
        return;
    }
    
    // Handle both string and object formats
    let questionText = '';
    if (typeof question === 'string') {
        questionText = question;
    } else if (typeof question === 'object') {
        if (typeof question.text === 'string') {
            questionText = question.text;
        } else if (typeof question.text === 'object') {
            // If text itself is an object, try to extract from it
            questionText = question.text.text || JSON.stringify(question.text);
        } else {
            questionText = question.question || JSON.stringify(question);
        }
    }
    
    if (!questionText || questionText === '[object Object]') {
        console.error('Question text missing or invalid:', question);
        console.error('Question structure:', JSON.stringify(question, null, 2));
        showToast('Invalid question format. Please contact support.', 'error');
        return;
    }
    
    document.getElementById('current-question-num').textContent = index + 1;
    document.getElementById('question-number').textContent = index + 1;
    document.getElementById('question-text').textContent = questionText;
    
    const progress = ((index + 1) / questions.length) * 100;
    document.getElementById('progress-bar').style.width = progress + '%';
    
    currentAnswerTranscript = '';
    finalTranscripts = [];
    
    // Clear textarea
    const textarea = document.getElementById('answer-textarea');
    if (textarea) {
        textarea.value = '';
    }
    
    // Clear temp values
    window.tempInterimValue = '';
}

async function toggleRecording() {
    const btn = document.getElementById('record-btn');
    const icon = document.getElementById('record-icon');
    const text = document.getElementById('record-text');
    
    if (!deepgramSTT.isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 48000
                }
            });
            
            await deepgramSTT.startRecording(stream);
            
            icon.textContent = '⏸';
            text.textContent = 'Stop Speaking';
            btn.classList.add('recording');
            
        } catch (error) {
            showToast('Microphone access required', 'error');
        }
        
    } else {
        // Just stop recording, don't submit
        deepgramSTT.stopRecording();
        
        icon.textContent = '▶️';
        text.textContent = 'Start Speaking';
        btn.classList.remove('recording');
        
        // Update the textarea with final transcript
        const textarea = document.getElementById('answer-textarea');
        if (textarea) {
            textarea.value = currentAnswerTranscript;
        }
    }
}

function displayLiveTranscript(transcript, isFinal) {
    const textarea = document.getElementById('answer-textarea');
    
    if (!textarea) return;
    
    if (isFinal) {
        // Append final transcript to existing content
        const currentValue = textarea.value;
        const newValue = currentValue + (currentValue ? ' ' : '') + transcript;
        textarea.value = newValue;
        
        // Scroll to bottom
        textarea.scrollTop = textarea.scrollHeight;
    } else {
        // Show interim result without saving
        // Store current final value
        if (!window.tempInterimValue) {
            window.tempInterimValue = textarea.value;
        }
        
        // Show interim appended to final
        textarea.value = window.tempInterimValue + (window.tempInterimValue ? ' ' : '') + transcript;
        textarea.scrollTop = textarea.scrollHeight;
    }
}

async function submitAnswer() {
    const textarea = document.getElementById('answer-textarea');
    const transcriptText = textarea ? textarea.value.trim() : currentAnswerTranscript.trim();
    
    if (!transcriptText || transcriptText.length === 0) {
        showToast('Please provide an answer before submitting', 'warning');
        return;
    }
    
    try {
        showToast('Saving your answer...', 'info');
        
        await apiCall(`/interviews/${interviewId}/submit-answer`, {
            method: 'POST',
            body: JSON.stringify({
                question_id: questions[currentQuestionIndex].question_id,
                transcription: transcriptText
            })
        });
        
        showToast('Answer saved!', 'success');
        
        setTimeout(() => {
            if (currentQuestionIndex < questions.length - 1) {
                showQuestion(currentQuestionIndex + 1);
            } else {
                completeInterview();
            }
        }, 1000);
        
    } catch (error) {
        console.error('Save answer error:', error);
        showToast('Failed to save answer. Please try again.', 'error');
    }
}

async function skipQuestion() {
    if (confirm('Skip this question? You won\'t be able to come back.')) {
        const textarea = document.getElementById('answer-textarea');
        if (textarea) {
            textarea.value = '[Question skipped by candidate]';
        }
        currentAnswerTranscript = '[Question skipped by candidate]';
        await submitAnswer();
    }
}

async function completeInterview() {
    try {
        // Stop total timer
        stopTotalTimer();
        
        // Stop proctoring
        if (proctoringService) {
            proctoringService.stop();
        }
        
        // Show blocking upload modal
        showUploadBlockingModal();
        
        // Stop video recording
        if (completeVideoRecorder && completeVideoRecorder.state === 'recording') {
            completeVideoRecorder.stop();
            
            // Wait for the onstop event and ensure all chunks are collected
            await new Promise(resolve => {
                completeVideoRecorder.onstop = () => {
                    console.log('Video recorder stopped. Total chunks:', completeVideoChunks.length);
                    setTimeout(resolve, 500);
                };
            });
        }
        
        // Stop camera stream
        const video = document.getElementById('interview-video');
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
            video.srcObject = null;
        }
        
        // Check if we have video chunks
        if (completeVideoChunks.length === 0) {
            console.error('No video chunks recorded!');
        } else {
            console.log('Creating video blob from', completeVideoChunks.length, 'chunks');
            
            const videoBlob = new Blob(completeVideoChunks, { 
                type: 'video/webm;codecs=vp9,opus' 
            });
            
            console.log('Video blob size:', videoBlob.size, 'bytes');
            
            if (videoBlob.size > 0) {
                // Upload video
                await uploadCompleteVideo(videoBlob);
            }
        }
        
        // Mark interview as complete with auto-submit parameters
        await apiCall(`/interviews/${interviewId}/complete`, {
            method: 'POST',
            body: JSON.stringify({
                auto_submitted: isAutoSubmitted,
                auto_submit_reason: isAutoSubmitted ? 'multiple_tab_switches' : null
            })
        });
        
        // Update modal to show success
        updateUploadModalSuccess();
        
        setTimeout(() => {
            window.location.href = '/candidate.html?completed=true';
        }, 2000);
        
    } catch (error) {
        console.error('Complete interview error:', error);
        updateUploadModalSuccess(); // Still redirect even on error
        setTimeout(() => {
            window.location.href = '/candidate.html?completed=true';
        }, 2000);
    }
}

async function uploadCompleteVideo(videoBlob) {
    const formData = new FormData();
    formData.append('video_file', videoBlob, 'interview.webm');
    
    const response = await fetch(
        `${API_BASE_URL}/interviews/${interviewId}/upload-video`,
        {
            method: 'POST',
            body: formData
        }
    );
    
    if (!response.ok) throw new Error('Video upload failed');
    
    return await response.json();
}

function toggleMic() {
    const video = document.getElementById('interview-video');
    const micBtn = document.getElementById('mic-btn');
    const micIcon = document.getElementById('mic-icon');
    
    if (!video.srcObject) return;
    
    const audioTrack = video.srcObject.getAudioTracks()[0];
    if (audioTrack) {
        // If trying to mute, show popup and keep it on
        if (audioTrack.enabled) {
            showMicWarningModal();
            return; // Don't proceed with muting
        } else {
            // If already muted, allow unmuting
            audioTrack.enabled = true;
            isMicMuted = false;
            micIcon.textContent = '🎤';
            micBtn.classList.remove('muted');
            showToast('Microphone unmuted', 'success');
        }
    } else {
        // If audio track not found, still show the warning modal
        showMicWarningModal();
    }
}

function showMicWarningModal() {
    const modal = document.createElement('div');
    modal.className = 'feature-modal';
    modal.innerHTML = `
        <div class="feature-modal-content">
            <div class="feature-icon">🎤</div>
            <h2>Microphone Required</h2>
            <p class="feature-message">
                Please keep your microphone ON during the interview. This is required to record your answers.
            </p>
            <p class="feature-warning">
                Click OK to acknowledge and continue with your interview.
            </p>
            <button class="btn-primary btn-lg" onclick="this.closest('.feature-modal').remove()">
                OK, Keep Microphone ON
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function toggleVideo() {
    const video = document.getElementById('interview-video');
    const videoBtn = document.getElementById('video-btn');
    const videoIcon = document.getElementById('video-icon');
    
    if (!video.srcObject) return;
    
    const videoTrack = video.srcObject.getVideoTracks()[0];
    if (videoTrack) {
        // If trying to turn off camera, show popup and keep it on
        if (videoTrack.enabled) {
            showCameraWarningModal();
        } else {
            // If already off, allow turning on
            videoTrack.enabled = true;
            isVideoOff = false;
            videoIcon.textContent = '📷';
            videoBtn.classList.remove('video-off');
            showToast('Camera turned on', 'success');
        }
    }
}

function showCameraWarningModal() {
    const modal = document.createElement('div');
    modal.className = 'feature-modal';
    modal.innerHTML = `
        <div class="feature-modal-content">
            <div class="feature-icon">📷</div>
            <h2>Camera Required</h2>
            <p class="feature-message">
                Please keep your camera ON during the interview. This is required to record your video interview.
            </p>
            <p class="feature-warning">
                Click OK to acknowledge and continue with your interview.
            </p>
            <button class="btn-primary btn-lg" onclick="this.closest('.feature-modal').remove()">
                OK, Keep Camera ON
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
}


function startTotalTimer() {
    totalTimeRemaining = 1500; // 25 minutes
    updateTotalTimerDisplay();
    
    timerInterval = setInterval(() => {
        totalTimeRemaining--;
        updateTotalTimerDisplay();
        
        // Warning at 5 minutes remaining
        if (totalTimeRemaining <= 300) {
            document.getElementById('timer-value').classList.add('warning');
        }
        
        // Auto-submit when time runs out
        if (totalTimeRemaining <= 0) {
            stopTotalTimer();
            showToast('Time is up! Auto-submitting interview...', 'warning');
            completeInterview();
        }
    }, 1000);
}

function stopTotalTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function updateTotalTimerDisplay() {
    const minutes = Math.floor(totalTimeRemaining / 60);
    const seconds = totalTimeRemaining % 60;
    document.getElementById('timer-value').textContent = 
        `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function showUploadBlockingModal() {
    const modal = document.createElement('div');
    modal.id = 'upload-blocking-modal';
    modal.className = 'feature-modal';
    modal.style.zIndex = '99999';
    modal.innerHTML = `
        <div class="feature-modal-content" style="max-width: 500px;">
            <div class="feature-icon" style="font-size: 3rem;">📤</div>
            <h2 style="color: var(--primary); margin-bottom: 1rem;">Uploading Video...</h2>
            <p class="feature-message" style="margin-bottom: 1.5rem;">
                Please wait while we upload your interview video. This may take a few moments.
            </p>
            <div class="feature-warning" style="background: #fef2f2; border: 2px solid #ef4444; color: #991b1b; padding: 1rem; border-radius: 8px; font-weight: 600;">
                ⚠️ DO NOT refresh or close this page!
            </div>
            <div style="margin-top: 1.5rem;">
                <div class="spinner" style="width: 3rem; height: 3rem; border: 4px solid rgba(59, 130, 246, 0.3); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto;"></div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function updateUploadModalSuccess() {
    const modal = document.getElementById('upload-blocking-modal');
    if (modal) {
        modal.querySelector('.feature-modal-content').innerHTML = `
            <div class="feature-icon" style="font-size: 3rem;">✅</div>
            <h2 style="color: #10b981; margin-bottom: 1rem;">Upload Complete!</h2>
            <p class="feature-message">
                Your interview has been successfully uploaded. Redirecting you now...
            </p>
        `;
    }
}

// ── Face Verification ──────────────────────────────────────────────────────────

async function initializeFaceVerification() {
    const urlParams = new URLSearchParams(window.location.search);
    const faceVerifyEnabled = urlParams.get('face_verify') === '1';
    const screeningId = urlParams.get('screening_id');

    if (!faceVerifyEnabled || !screeningId) {
        console.log('[FaceVerify] Not enabled for this interview.');
        return;
    }

    if (typeof FaceVerificationService === 'undefined') {
        console.warn('[FaceVerify] FaceVerificationService not loaded');
        return;
    }

    faceVerificationService = new FaceVerificationService();

    // Load models (face-api.js must be loaded first via defer script)
    const modelsReady = await waitForFaceApi();
    if (!modelsReady) {
        showToast('Face verification library did not load. Proceeding without identity check.', 'warning');
        return;
    }

    const loaded = await faceVerificationService.loadModels();
    if (!loaded) return;

    const photoLoaded = await faceVerificationService.loadReferencePhoto(screeningId);
    if (!photoLoaded) {
        console.warn('[FaceVerify] Could not load reference photo, skipping verification');
        faceVerificationService = null;
        return;
    }

    faceVerificationService.start();
    console.log('[FaceVerify] ✅ Face verification active');
}

// Wait for face-api.js to finish loading (it's deferred)
function waitForFaceApi(timeoutMs = 15000) {
    return new Promise((resolve) => {
        if (typeof faceapi !== 'undefined') {
            resolve(true);
            return;
        }
        const start = Date.now();
        const check = setInterval(() => {
            if (typeof faceapi !== 'undefined') {
                clearInterval(check);
                resolve(true);
            } else if (Date.now() - start > timeoutMs) {
                clearInterval(check);
                console.warn('[FaceVerify] face-api.js did not load in time');
                resolve(false);
            }
        }, 200);
    });
}

// ───────────────────────────────────────────────────────────────────────────────

function exitInterview() {
    if (confirm('Are you sure you want to exit? Your progress will be lost.')) {
        if (proctoringService) {
            proctoringService.stop();
        }
        if (faceVerificationService) {
            faceVerificationService.stop();
        }
        if (completeVideoRecorder && completeVideoRecorder.state === 'recording') {
            completeVideoRecorder.stop();
        }
        if (deepgramSTT && deepgramSTT.isRecording) {
            deepgramSTT.stopRecording();
        }
        const video = document.getElementById('interview-video');
        if (video && video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
        window.location.href = '/candidate.html';
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (proctoringService) {
        proctoringService.stop();
    }
    if (faceVerificationService) {
        faceVerificationService.stop();
    }
    const video = document.getElementById('interview-video');
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
    }
});
