// Candidate Page JavaScript
let permissionsGranted = false;
let mediaStream = null;
let invitationData = null;

// Tab Switching
function switchTab(tabName, buttonElement) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(`tab-${tabName}`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate button
    if (buttonElement) {
        buttonElement.classList.add('active');
    }
}

// Verify Invitation Code
async function verifyInvitationCode() {
    const codeInput = document.getElementById('invitation-code-input');
    const code = codeInput.value.trim().toUpperCase();
    
    if (!code || code.length !== 8) {
        showToast('Please enter a valid 8-character invitation code', 'error');
        return;
    }
    
    try {
        showToast('Verifying your invitation code...', 'info');
        
        // Call API to verify code (POST request)
        const response = await apiCall(`/invitations/verify?invitation_code=${code}`, {
            method: 'POST'
        });
        
        if (response) {
            invitationData = response;
            showToast('Code verified successfully!', 'success');
            
            // Hide code entry section and show interview section
            document.getElementById('code-entry-section').style.display = 'none';
            document.getElementById('interview-section').style.display = 'block';
            
            // Update page header with job title
            if (response.jd_title) {
                const header = document.querySelector('.page-header p');
                header.textContent = `Position: ${response.jd_title} | Get ready for your AI interview`;
            }
        }
    } catch (error) {
        console.error('Verification error:', error);
        showToast(error.message || 'Invalid or expired invitation code. Please check and try again.', 'error');
        codeInput.value = '';
        codeInput.focus();
    }
}

// Request Permissions (MANDATORY)
async function requestPermissions() {
    const btn = document.getElementById('permission-btn');
    btn.disabled = true;
    btn.textContent = 'Checking...';
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: true, 
            audio: true 
        });
        
        mediaStream = stream;
        permissionsGranted = true;
        
        // Update UI
        updatePermissionUI(true);
        
        // Show video preview
        const videoPreview = document.getElementById('video-preview');
        const video = document.getElementById('preview-video');
        if (videoPreview && video) {
            videoPreview.style.display = 'block';
            video.srcObject = stream;
            video.style.display = 'block';
            const placeholder = document.querySelector('.video-placeholder');
            if (placeholder) {
                placeholder.style.display = 'none';
            }
        }
        
        showToast('Camera and microphone access granted!', 'success');
        document.getElementById('start-interview-btn').disabled = false;
        
    } catch (error) {
        console.error('Permission error:', error);
        showToast('Camera and microphone access is required to proceed with the interview. Please allow permissions and try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Allow Access';
    }
}

// Update Permission UI
function updatePermissionUI(granted) {
    const cameraIcon = document.getElementById('camera-icon');
    const micIcon = document.getElementById('mic-icon');
    const title = document.getElementById('permission-title');
    const desc = document.getElementById('permission-desc');
    const btn = document.getElementById('permission-btn');
    
    if (granted) {
        cameraIcon.classList.add('granted');
        micIcon.classList.add('granted');
        title.textContent = 'Permissions Granted ✅';
        desc.textContent = 'Camera and microphone are ready';
        btn.style.display = 'none';
    }
}

// Start Interview (permissions required)
async function startInterview() {
    if (!permissionsGranted) {
        showToast('You must grant camera and microphone permissions before starting the interview', 'error');
        return;
    }
    
    if (!invitationData) {
        showToast('Invalid session. Please refresh and enter your invitation code again.', 'error');
        return;
    }
    
    try {
        showToast('Starting your AI interview...', 'success');
        
        // Create interview from invitation
        const response = await apiCall(`/invitations/${invitationData.invitation_code}/start-interview`, {
            method: 'POST'
        });
        
        if (response && response.interview_id) {
            // Navigate to interview page with interview ID and face verification info
            const faceVerification = invitationData.face_verification_enabled ? '&face_verify=1' : '';
            const screeningId = invitationData.screening_id ? `&screening_id=${invitationData.screening_id}` : '';
            setTimeout(() => {
                window.location.href = `/interview.html?id=${response.interview_id}${faceVerification}${screeningId}`;
            }, 1000);
        } else {
            throw new Error('Failed to create interview session');
        }
        
    } catch (error) {
        console.error('Start interview error:', error);
        showToast(error.message || 'Failed to start interview', 'error');
    }
}

// Toggle FAQ
function toggleFaq(element) {
    const faqItem = element.closest('.faq-item');
    if (faqItem) {
        faqItem.classList.toggle('active');
    }
}

// Setup event listeners on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if coming from completed interview
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('completed') === 'true') {
        document.getElementById('code-entry-section').style.display = 'none';
        document.getElementById('interview-section').style.display = 'none';
        document.getElementById('completion-message').style.display = 'block';
        document.querySelector('.page-header p').textContent = 'Your interview has been successfully submitted';
        return;
    }
    
    // Focus on code input
    const codeInput = document.getElementById('invitation-code-input');
    if (codeInput) {
        codeInput.focus();
        
        // Allow Enter key to submit code
        codeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                verifyInvitationCode();
            }
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }
});
