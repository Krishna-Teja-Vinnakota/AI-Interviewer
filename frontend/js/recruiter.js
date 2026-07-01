// Recruiter Page JavaScript
let selectedFiles = [];
let jobDescriptions = [];
let batchResults = [];

// Tab Switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const selectedTab = document.getElementById(`tab-${tabName}`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    event.target.classList.add('active');
    
    // Load data based on tab
    if (tabName === 'history') {
        loadInterviewHistory();
    } else if (tabName === 'jd-management') {
        loadJDList();
    }
}

// Load Job Descriptions
async function loadJobDescriptions() {
    try {
        const response = await apiCall('/jds');
        jobDescriptions = response;
        
        const select = document.getElementById('jd-select');
        select.innerHTML = '<option value="">Choose a job description...</option>';
        
        response.forEach(jd => {
            const option = document.createElement('option');
            option.value = jd.jd_id;
            option.textContent = jd.title;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load job descriptions:', error);
    }
}

// Handle File Select
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    
    const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    
    let validFiles = [];
    let invalidCount = 0;
    
    for (const file of files) {
        // Validate file type
        if (!validTypes.includes(file.type)) {
            invalidCount++;
            continue;
        }
        
        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast(`${file.name} exceeds 10MB limit`, 'error');
            continue;
        }
        
        validFiles.push(file);
    }
    
    if (invalidCount > 0) {
        showToast(`${invalidCount} file(s) skipped - invalid format`, 'error');
    }
    
    if (validFiles.length > 0) {
        selectedFiles = [...selectedFiles, ...validFiles];
        displayFilesPreview();
        checkFormValidity();
        showToast(`${validFiles.length} resume(s) added`, 'success');
    }
}

// Display Files Preview
function displayFilesPreview() {
    const preview = document.getElementById('files-preview');
    const filesList = document.getElementById('files-list');
    const filesCount = document.getElementById('files-count');
    
    if (!preview || !filesList) return;
    
    filesCount.textContent = selectedFiles.length;
    preview.style.display = selectedFiles.length > 0 ? 'block' : 'none';
    
    filesList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <span class="file-icon">📄</span>
                <div>
                    <p class="file-name">${file.name}</p>
                    <p class="file-size">${formatFileSize(file.size)}</p>
                </div>
            </div>
            <button class="btn-ghost btn-sm" onclick="removeFile(${index})">✕</button>
        </div>
    `).join('');
}

// Remove Single File
function removeFile(index) {
    selectedFiles.splice(index, 1);
    displayFilesPreview();
    checkFormValidity();
    
    if (selectedFiles.length === 0) {
        document.getElementById('resume-upload').value = '';
    }
}

// Remove All Files
function removeAllFiles() {
    selectedFiles = [];
    document.getElementById('files-preview').style.display = 'none';
    document.getElementById('resume-upload').value = '';
    checkFormValidity();
    showToast('All files removed', 'info');
}

// Check Form Validity
function checkFormValidity() {
    const jdSelect = document.getElementById('jd-select');
    const startBtn = document.getElementById('start-screening-btn');
    
    if (startBtn) {
        startBtn.disabled = !(selectedFiles.length > 0 && jdSelect.value);
    }
}

// Start Screening
async function startScreening() {
    if (selectedFiles.length === 0) {
        showToast('Please upload at least one resume', 'error');
        return;
    }
    
    const jdSelect = document.getElementById('jd-select');
    if (!jdSelect.value) {
        showToast('Please select a job description', 'error');
        return;
    }
    
    const btn = document.getElementById('start-screening-btn');
    const btnText = document.getElementById('btn-text');
    
    btn.disabled = true;
    batchResults = [];
    
    try {
        showToast(`Processing ${selectedFiles.length} resume(s)...`, 'info');
        
        // Process each resume
        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            btnText.innerHTML = `<span class="spinner"></span> Processing ${i + 1}/${selectedFiles.length}...`;
            
            try {
                // Upload resume
                const uploadResult = await uploadFile('/resumes/upload', file);
                
                if (!uploadResult.resume_id) {
                    batchResults.push({
                        fileName: file.name,
                        status: 'error',
                        error: 'Upload failed'
                    });
                    continue;
                }
                
                // Match with JD
                const matchResult = await apiCall(`/resumes/${uploadResult.resume_id}/match`, {
                    method: 'POST',
                    body: JSON.stringify({ jd_id: jdSelect.value })
                });
                
                batchResults.push({
                    fileName: file.name,
                    resumeId: uploadResult.resume_id,
                    candidateId: uploadResult.candidate_id,
                    status: 'success',
                    ...matchResult
                });
                
            } catch (error) {
                console.error(`Error processing ${file.name}:`, error);
                batchResults.push({
                    fileName: file.name,
                    status: 'error',
                    error: error.message || 'Processing failed'
                });
            }
        }
        
        // Show results
        showBatchResults();
        
        // Reset form
        selectedFiles = [];
        jdSelect.value = '';
        document.getElementById('files-preview').style.display = 'none';
        document.getElementById('resume-upload').value = '';
        checkFormValidity();
        
        showToast('Screening completed and saved!', 'success');
        
    } catch (error) {
        console.error('Batch screening error:', error);
        showToast('Failed to complete screening process', 'error');
    } finally {
        btn.disabled = false;
        btnText.innerHTML = '▶️ Start AI Screening';
    }
}

// Load Saved Screening Results
async function loadScreeningResults(jdId = null) {
    try {
        const url = jdId ? `/screening-results?jd_id=${jdId}` : '/screening-results';
        const results = await apiCall(url);
        
        if (results.length === 0) {
            // Don't show results div if no results
            const resultsDiv = document.getElementById('batch-results');
            if (resultsDiv) {
                resultsDiv.style.display = 'none';
            }
            return;
        }
        
        // Convert to batch results format
        batchResults = results.map(r => ({
            fileName: r.file_name,
            screening_id: r.screening_id,
            screeningStatus: r.status,  // pending, invited, rejected_by_candidate, call_in_progress
            status: 'success',
            match_score: r.overall_match_score / 100,  // Normalize to 0-1 for backward compatibility
            overall_match_score: r.overall_match_score,
            final_recommendation: r.final_recommendation,
            recommendation_action: r.recommendation_action,
            recommendation: r.recommendation_action,
            face_verification_enabled: r.face_verification_enabled || false
        }));
        
        showBatchResults();
    } catch (error) {
        console.error('Failed to load screening results:', error);
    }
}

// Load Interview History
async function loadInterviewHistory() {
    try {
        const response = await apiCall('/interviews?status=completed');
        const historyList = document.getElementById('history-list');
        
        if (!historyList) return;
        
        if (response.length === 0) {
            historyList.innerHTML = '<p style="text-align: center; color: var(--muted-foreground); padding: 2rem;">No interview history yet</p>';
            return;
        }
        
        historyList.innerHTML = response.map(interview => {
            // Format date properly - handle null/undefined dates
            let dateStr = 'N/A';
            if (interview.scheduled_time) {
                const date = new Date(interview.scheduled_time);
                if (!isNaN(date.getTime())) {
                    dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                }
            }
            
            return `
                <div class="history-item">
                    <div class="history-info">
                        <h4>${interview.candidate_name || 'Unknown Candidate'}</h4>
                        <p>Interview ID: ${interview.interview_id}</p>
                    </div>
                    <div class="history-meta">
                        <div class="meta-item">
                            <p class="meta-label">Date</p>
                            <p class="meta-value">${dateStr}</p>
                        </div>
                        <button class="btn-outline btn-sm" onclick="viewInterviewDetails('${interview.interview_id}')">View Details</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// View Interview Details
async function viewInterviewDetails(interviewId) {
    try {
        showToast('Loading interview details...', 'info');
        
        // Get interview data
        const interview = await apiCall(`/interviews/${interviewId}`);
        
        // Check if analysis exists
        let analysis = null;
        let analysisStatus = 'pending';
        
        try {
            const analysisResult = await apiCall(`/interviews/${interviewId}/results`);
            if (analysisResult && analysisResult.status === 'completed') {
                analysis = analysisResult;
                analysisStatus = 'completed';
            } else {
                analysisStatus = 'not_started';
            }
        } catch (error) {
            analysisStatus = 'not_started';
        }
        
        // Show modal with interview details
        showInterviewDetailsModal(interview, analysis, analysisStatus);
        
    } catch (error) {
        console.error('Error loading interview details:', error);
        showToast('Failed to load interview details', 'error');
    }
}

function showInterviewDetailsModal(interview, analysis, analysisStatus) {
    const modal = document.createElement('div');
    modal.className = 'jd-modal';
    modal.id = 'interview-details-modal';
    modal.innerHTML = `
        <div class="jd-modal-content" style="max-width: 1200px; max-height: 90vh; overflow-y: auto;">
            <div class="jd-modal-header">
                <h2>Interview Details - ${interview.candidate_name || 'Candidate'}</h2>
                <button class="btn-ghost" onclick="this.closest('.jd-modal').remove()">✕</button>
            </div>
            <div class="jd-modal-body">
                <!-- Interview Status -->
                <div class="jd-section">
                    <h4>📋 Interview Information</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Status</p>
                            <p style="text-transform: capitalize;">${interview.status.replace('_', ' ')}</p>
                        </div>
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Questions</p>
                            <p>${interview.questions ? interview.questions.length : 0} questions</p>
                        </div>
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Started</p>
                            <p>${interview.started_at ? new Date(interview.started_at).toLocaleString() : 'N/A'}</p>
                        </div>
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Completed</p>
                            <p>${interview.completed_at ? new Date(interview.completed_at).toLocaleString() : 'N/A'}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Video Section -->
                ${interview.video_url ? `
                <div class="jd-section">
                    <h4>🎥 Interview Recording</h4>
                    <video controls width="100%" preload="metadata" style="border-radius: 8px; margin-bottom: 1rem;">
                        <source src="${interview.video_url}" type="video/webm">
                        Your browser does not support the video tag.
                    </video>
                    <p><strong>Video URL:</strong> <a href="${interview.video_url}" target="_blank">${interview.video_url}</a></p>
                    ${interview.video_size ? `<p><strong>Size:</strong> ${formatFileSize(interview.video_size)}</p>` : ''}
                    ${interview.video_uploaded_at ? `<p><strong>Uploaded:</strong> ${new Date(interview.video_uploaded_at).toLocaleString()}</p>` : ''}
                </div>
                ` : `
                <div class="jd-section">
                    <h4>🎥 Interview Recording</h4>
                    <p style="color: var(--muted-foreground);">No video uploaded yet</p>
                </div>
                `}
                
                <!-- Analysis Section -->
                <div class="jd-section" id="analysis-section">
                    <h4>🤖 AI Analysis</h4>
                    ${analysisStatus === 'completed' && analysis ? `
                        <div style="background: #f0fdf4; padding: 1.5rem; border-radius: var(--radius); border-left: 4px solid #10b981; margin-top: 1rem;">
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 1rem;">
                                <div>
                                    <p style="font-weight: 600; margin-bottom: 0.3rem; color: #065f46;">Overall Score</p>
                                    <p style="font-size: 2rem; font-weight: bold; color: #10b981;">${analysis.overall_score}/10</p>
                                </div>
                                <div>
                                    <p style="font-weight: 600; margin-bottom: 0.3rem; color: #065f46;">Recommendation</p>
                                    <p style="font-size: 1.5rem; font-weight: bold; text-transform: uppercase; color: ${
                                        analysis.recommendation === 'proceed' ? '#10b981' : 
                                        analysis.recommendation === 'reject' ? '#ef4444' : '#f59e0b'
                                    };">${analysis.recommendation}</p>
                                </div>
                            </div>
                            <button class="btn-primary" onclick="viewFullReport('${interview.interview_id}')">
                                📊 View Full Analysis Report
                            </button>
                        </div>
                    ` : `
                        <div style="background: #eff6ff; padding: 1.5rem; border-radius: var(--radius); border-left: 4px solid #3b82f6; margin-top: 1rem;">
                            <p style="margin-bottom: 1rem; color: #1e40af;">Analysis has not been run yet. Click the button below to analyze this interview.</p>
                            <button class="btn-primary btn-lg" id="analyze-btn" onclick="triggerAnalysisFromDetails('${interview.interview_id}')">
                                <span>🔍</span> Analyze Interview Now
                            </button>
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

async function triggerAnalysisFromDetails(interviewId) {
    const analyzeBtn = document.getElementById('analyze-btn');
    const analysisSection = document.getElementById('analysis-section');
    
    if (!analyzeBtn || !analysisSection) return;
    
    try {
        // Disable button and show loading
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner"></span> Analyzing...';
        
        showToast('Starting AI analysis...', 'info');
        
        // Trigger analysis
        await apiCall(`/interviews/${interviewId}/analyze`, {
            method: 'POST'
        });
        
        showToast('Analysis in progress...', 'info');
        
        // Poll for results
        let attempts = 0;
        const maxAttempts = 30; // 30 seconds max
        
        const checkAnalysis = setInterval(async () => {
            attempts++;
            
            try {
                const analysis = await apiCall(`/interviews/${interviewId}/results`);
                
                if (analysis.status === 'completed') {
                    clearInterval(checkAnalysis);
                    
                    // Update UI with results
                    analysisSection.innerHTML = `
                        <h4>🤖 AI Analysis</h4>
                        <div style="background: #f0fdf4; padding: 1.5rem; border-radius: var(--radius); border-left: 4px solid #10b981; margin-top: 1rem;">
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 1rem;">
                                <div>
                                    <p style="font-weight: 600; margin-bottom: 0.3rem; color: #065f46;">Overall Score</p>
                                    <p style="font-size: 2rem; font-weight: bold; color: #10b981;">${analysis.overall_score}/10</p>
                                </div>
                                <div>
                                    <p style="font-weight: 600; margin-bottom: 0.3rem; color: #065f46;">Recommendation</p>
                                    <p style="font-size: 1.5rem; font-weight: bold; text-transform: uppercase; color: ${
                                        analysis.recommendation === 'proceed' ? '#10b981' : 
                                        analysis.recommendation === 'reject' ? '#ef4444' : '#f59e0b'
                                    };">${analysis.recommendation}</p>
                                </div>
                            </div>
                            <button class="btn-primary" onclick="viewFullReport('${interviewId}')">
                                📊 View Full Analysis Report
                            </button>
                        </div>
                    `;
                    
                    showToast('Analysis completed!', 'success');
                }
            } catch (error) {
                // Still processing
            }
            
            if (attempts >= maxAttempts) {
                clearInterval(checkAnalysis);
                showToast('Analysis is taking longer than expected. Please refresh and check again.', 'warning');
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<span>🔍</span> Retry Analysis';
            }
        }, 1000);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showToast('Failed to start analysis: ' + error.message, 'error');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<span>🔍</span> Analyze Interview Now';
    }
}

async function viewFullReport(interviewId) {
    try {
        const report = await apiCall(`/interviews/${interviewId}/report`);
        
        // Open report in new modal
        const modal = document.createElement('div');
        modal.className = 'jd-modal';
        modal.innerHTML = `
            <div class="jd-modal-content" style="max-width: 900px;">
                <div class="jd-modal-header">
                    <h2>📊 Full Analysis Report</h2>
                    <button class="btn-ghost" onclick="this.closest('.jd-modal').remove()">✕</button>
                </div>
                <div class="jd-modal-body">
                    <!-- Overall Score -->
                    <div class="jd-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 2rem;">
                        <h3 style="color: white; margin-bottom: 1rem;">Overall Score</h3>
                        <p style="font-size: 3rem; font-weight: bold; margin: 0;">${report.overall_score}/10</p>
                        <p style="font-size: 1.25rem; margin-top: 0.5rem; text-transform: uppercase;">${report.recommendation}</p>
                    </div>
                    
                    <!-- Strengths -->
                    ${report.strengths && report.strengths.length > 0 ? `
                    <div class="jd-section" style="background: #f0fdf4; border-left: 4px solid #10b981;">
                        <h4 style="color: #10b981;">✅ Strengths</h4>
                        <ul style="margin-left: 1.5rem; line-height: 1.8;">
                            ${report.strengths.map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    
                    <!-- Weaknesses -->
                    ${report.weaknesses && report.weaknesses.length > 0 ? `
                    <div class="jd-section" style="background: #fef2f2; border-left: 4px solid #ef4444;">
                        <h4 style="color: #ef4444;">⚠️ Weaknesses</h4>
                        <ul style="margin-left: 1.5rem; line-height: 1.8;">
                            ${report.weaknesses.map(w => `<li>${w}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    
                    <!-- Question Analysis -->
                    <div class="jd-section">
                        <h4>📝 Question-by-Question Analysis</h4>
                        ${report.question_analysis && report.question_analysis.length > 0 ? 
                            report.question_analysis.map((qa, index) => `
                                <div style="background: #ffffff; padding: 1.5rem; border-radius: var(--radius); margin-top: 1rem; border: 2px solid ${
                                    qa.score >= 7 ? '#10b981' : qa.score >= 5 ? '#f59e0b' : '#ef4444'
                                }; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <!-- Question Number & Score -->
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 2px solid #e5e7eb;">
                                        <h5 style="margin: 0; font-size: 1.1rem; color: #1f2937;">Question ${index + 1}</h5>
                                        <span style="background: ${
                                            qa.score >= 7 ? '#10b981' : qa.score >= 5 ? '#f59e0b' : '#ef4444'
                                        }; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold; font-size: 1rem;">
                                            Score: ${qa.score}/10
                                        </span>
                                    </div>
                                    
                                    <!-- Question Text -->
                                    <div style="margin-bottom: 1.25rem;">
                                        <p style="font-weight: 600; color: #374151; margin-bottom: 0.5rem; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.5px;">
                                            ❓ Question:
                                        </p>
                                        <p style="color: #1f2937; font-size: 1rem; line-height: 1.6; background: #f9fafb; padding: 0.75rem; border-radius: 6px; margin: 0;">
                                            ${typeof qa.question === 'string' ? qa.question : (qa.question?.text || 'Question ' + (index + 1))}
                                        </p>
                                    </div>
                                    
                                    <!-- Candidate's Answer -->
                                    <div style="margin-bottom: 1.25rem;">
                                        <p style="font-weight: 600; color: #374151; margin-bottom: 0.5rem; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.5px;">
                                            💬 Candidate's Answer:
                                        </p>
                                        <p style="color: #4b5563; font-size: 0.95rem; line-height: 1.7; background: #eff6ff; padding: 1rem; border-radius: 6px; border-left: 4px solid #3b82f6; margin: 0; font-style: italic;">
                                            ${qa.answer || '[No answer provided]'}
                                        </p>
                                    </div>
                                    
                                    <!-- AI Justification/Feedback -->
                                    <div>
                                        <p style="font-weight: 600; color: #374151; margin-bottom: 0.5rem; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.5px;">
                                            🤖 AI Justification:
                                        </p>
                                        <p style="color: #374151; font-size: 0.95rem; line-height: 1.7; background: #fef3c7; padding: 1rem; border-radius: 6px; border-left: 4px solid #f59e0b; margin: 0;">
                                            ${qa.feedback || 'No feedback available'}
                                        </p>
                                    </div>
                                </div>
                            `).join('')
                        : '<p style="text-align: center; color: var(--muted-foreground); padding: 2rem;">No question analysis available</p>'}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
    } catch (error) {
        console.error('Error loading report:', error);
        showToast('Failed to load full report', 'error');
    }
}

function closeModal() {
    const modal = document.querySelector('.interview-modal');
    if (modal) modal.remove();
}

async function reAnalyzeInterview(interviewId) {
    const button = event.target;
    const originalText = button.innerHTML;
    
    try {
        // Update button to show progress
        button.disabled = true;
        button.innerHTML = '<span style="display: inline-block; width: 14px; height: 14px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite;"></span> Analyzing...';
        
        showToast('Starting AI analysis... This takes 1-2 minutes', 'info');
        
        // Trigger analysis
        await apiCall(`/interviews/${interviewId}/analyze`, { method: 'POST' });
        
        showToast('✅ Analysis completed! Refreshing report...', 'success');
        
        // Close current modal
        closeModal();
        
        // Wait 1 second then reopen with fresh data
        setTimeout(() => {
            viewInterviewDetails(interviewId);
        }, 1000);
        
    } catch (error) {
        console.error('Analysis error:', error);
        button.disabled = false;
        button.innerHTML = originalText;
        showToast('Failed to analyze interview', 'error');
    }
}

// Helper function to load video chunks (legacy support)
function loadVideoChunk(playerId, interviewId, fileId, chunkIndex) {
    const player = document.getElementById(playerId);
    if (player) {
        player.src = `/api/interviews/${interviewId}/media/${fileId}`;
        player.load();
        player.play();
        showToast(`Playing chunk ${chunkIndex + 1}`, 'info');
    }
}

// Trigger Analysis Manually
async function triggerAnalysis(interviewId) {
    const button = event.target;
    const originalText = button.innerHTML;
    
    try {
        // Update button to show progress
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> Analyzing...';
        
        showToast('Starting AI analysis... This may take 2-3 minutes', 'info');
        
        // Use force=true to re-analyze even if analysis exists
        await apiCall(`/interviews/${interviewId}/analyze?force=true`, { method: 'POST' });
        
        button.innerHTML = '✅ Analysis Started!';
        showToast('Analysis in progress! Processing images, video, and Q&A. Please check back in 2-3 minutes.', 'success');
        
        // Close modal and show instruction
        setTimeout(() => {
            document.querySelector('.jd-modal')?.remove();
            showToast('💡 Tip: Analysis is running in background. Refresh Interview History in 2-3 minutes to see results.', 'info');
        }, 3000);
        
    } catch (error) {
        console.error('Analysis error:', error);
        button.disabled = false;
        button.innerHTML = originalText;
        
        if (error.message && error.message.includes('Analysis already in progress')) {
            showToast('Analysis already in progress. Please wait...', 'warning');
        } else {
            showToast('Failed to trigger analysis. Please try again.', 'error');
        }
    }
}

// Placeholder functions for actions
function scheduleNextRound(interviewId) {
    showToast('Next round scheduling feature coming soon', 'info');
}

function downloadReport(interviewId) {
    showToast('Report download feature coming soon', 'info');
}

function sendToHR(interviewId) {
    showToast('HR notification feature coming soon', 'info');
}

// Toggle JD Form
function toggleJDForm() {
    const form = document.getElementById('jd-form');
    const listContainer = document.getElementById('jd-list-container');
    
    if (form.style.display === 'none') {
        form.style.display = 'block';
        listContainer.style.display = 'none';
        // Clear form
        document.getElementById('jd-title').value = '';
        document.getElementById('jd-location').value = '';
        document.getElementById('jd-experience').value = '';
        document.getElementById('jd-salary').value = '';
        document.getElementById('jd-notice').value = '';
        document.getElementById('jd-description').value = '';
        document.getElementById('jd-requirements').value = '';
        document.getElementById('jd-skills').value = '';
        form.querySelector('h3').textContent = 'Create New Job Description';
        editingJdId = null;
    } else {
        form.style.display = 'none';
        listContainer.style.display = 'block';
        editingJdId = null;
    }
}

// Save JD
async function saveJD() {
    const title = document.getElementById('jd-title').value.trim();
    const description = document.getElementById('jd-description').value.trim();
    const requirements = document.getElementById('jd-requirements').value.trim();
    const skillsText = document.getElementById('jd-skills').value.trim();
    const location = document.getElementById('jd-location').value.trim();
    const experience = document.getElementById('jd-experience').value.trim();
    const salary = document.getElementById('jd-salary').value.trim();
    const notice = document.getElementById('jd-notice').value.trim();
    
    if (!title || !description || !requirements) {
        showToast('Please fill in all required fields (Title, Description, Requirements)', 'error');
        return;
    }
    
    const skills = skillsText ? skillsText.split(',').map(s => s.trim()).filter(s => s) : [];
    
    const jdData = {
        title,
        description,
        requirements,
        skills,
        location: location || null,
        experience_required: experience || null,
        salary_range: salary || null,
        notice_period_acceptable: notice || null
    };
    
    try {
        if (editingJdId) {
            // Update existing JD
            showToast('Updating job description...', 'info');
            await apiCall(`/jds/${editingJdId}`, {
                method: 'PUT',
                body: JSON.stringify(jdData)
            });
            showToast('Job description updated!', 'success');
            editingJdId = null;
        } else {
            // Create new JD
            showToast('Creating job description...', 'info');
            await apiCall('/jds', {
                method: 'POST',
                body: JSON.stringify(jdData)
            });
            showToast('Job description created!', 'success');
        }
        
        toggleJDForm();
        loadJDList();
        loadJobDescriptions();
    } catch (error) {
        console.error('Failed to save JD:', error);
        showToast('Failed to save job description', 'error');
    }
}

// Load JD List
async function loadJDList() {
    try {
        const response = await apiCall('/jds');
        const jdList = document.getElementById('jd-list');
        
        if (!jdList) return;
        
        if (response.length === 0) {
            jdList.innerHTML = '<p style="text-align: center; color: var(--muted-foreground); padding: 2rem;">No job descriptions yet. Create one to get started.</p>';
            return;
        }
        
        jdList.innerHTML = response.map(jd => `
            <div class="jd-item">
                <div class="jd-info">
                    <h4>${jd.title}</h4>
                    <p>Created: ${new Date(jd.created_at).toLocaleDateString()}</p>
                </div>
                <div class="jd-actions">
                    <button class="btn-outline btn-sm" onclick="viewJDModal('${jd.jd_id}')">View</button>
                    <button class="btn-outline btn-sm" onclick="editJD('${jd.jd_id}')">Edit</button>
                    <button class="btn-ghost btn-sm" onclick="deleteJD('${jd.jd_id}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load JDs:', error);
    }
}


// Delete JD
async function deleteJD(jdId) {
    if (!confirm('Are you sure you want to delete this job description?')) {
        return;
    }
    
    try {
        await apiCall(`/jds/${jdId}`, { method: 'DELETE' });
        showToast('Job description deleted successfully', 'success');
        loadJDList();
        loadJobDescriptions();
    } catch (error) {
        console.error('Failed to delete JD:', error);
        showToast('Failed to delete job description', 'error');
    }
}

// Show Batch Results
function showBatchResults() {
    const resultsDiv = document.getElementById('batch-results');
    const summaryDiv = document.getElementById('results-summary');
    const tbody = document.getElementById('results-tbody');
    
    // Calculate summary
    const total = batchResults.length;
    const successful = batchResults.filter(r => r.status === 'success').length;
    
    // Use overall_match_score if available, otherwise fall back to match_score
    const strongMatch = batchResults.filter(r => {
        if (r.status !== 'success') return false;
        const score = r.overall_match_score !== undefined ? r.overall_match_score / 100 : r.match_score;
        return score >= 0.7;
    }).length;
    
    const moderateMatch = batchResults.filter(r => {
        if (r.status !== 'success') return false;
        const score = r.overall_match_score !== undefined ? r.overall_match_score / 100 : r.match_score;
        return score >= 0.5 && score < 0.7;
    }).length;
    
    const weakMatch = batchResults.filter(r => {
        if (r.status !== 'success') return false;
        const score = r.overall_match_score !== undefined ? r.overall_match_score / 100 : r.match_score;
        return score < 0.5;
    }).length;
    
    const errors = batchResults.filter(r => r.status === 'error').length;
    
    // Show summary
    summaryDiv.innerHTML = `
        <div class="summary-stats">
            <div class="summary-stat">
                <span class="summary-label">Total Processed</span>
                <span class="summary-value">${total}</span>
            </div>
            <div class="summary-stat success">
                <span class="summary-label">Strong Match</span>
                <span class="summary-value">${strongMatch}</span>
            </div>
            <div class="summary-stat warning">
                <span class="summary-label">Moderate Match</span>
                <span class="summary-value">${moderateMatch}</span>
            </div>
            <div class="summary-stat danger">
                <span class="summary-label">Weak Match</span>
                <span class="summary-value">${weakMatch}</span>
            </div>
            ${errors > 0 ? `<div class="summary-stat error">
                <span class="summary-label">Errors</span>
                <span class="summary-value">${errors}</span>
            </div>` : ''}
        </div>
    `;
    
    // Show table
    tbody.innerHTML = batchResults.map((result, index) => {
        if (result.status === 'error') {
            return `
                <tr>
                    <td>${result.fileName}</td>
                    <td colspan="3" class="error-cell">❌ ${result.error}</td>
                    <td></td>
                </tr>
            `;
        }
        
        // Use overall_match_score from LLM if available, otherwise fall back to semantic similarity
        const displayScore = result.overall_match_score !== undefined ? result.overall_match_score / 100 : result.match_score;
        const scorePercent = Math.round(displayScore * 100);
        let statusClass = '';
        let statusText = '';
        
        // Determine status based on overall match score or semantic similarity
        if (displayScore >= 0.7) {
            statusClass = 'status-success';
            statusText = 'Strong Match';
        } else if (displayScore >= 0.5) {
            statusClass = 'status-warning';
            statusText = 'Moderate Match';
        } else {
            statusClass = 'status-danger';
            statusText = 'Weak Match';
        }
        
        const hasScreeningId = result.screening_id;
        
        // Determine button based on screening status
        let actionButtons = '';
        
        if (hasScreeningId) {
            const photoUploaded = result.face_verification_enabled;
            const isInvited = result.screeningStatus === 'invited';
            actionButtons = `
                ${isInvited
                    ? `<span style="color: #10b981; font-weight: 600;">✅ Invited</span>`
                    : `<button class="btn-primary btn-sm" onclick="sendInvitation('${result.screening_id}')">📧 Send Invitation</button>
                       <button class="btn-ghost btn-sm" onclick="deleteScreeningResult('${result.screening_id}', ${index})">Delete</button>`
                }
                <label for="photo-upload-${result.screening_id}" class="btn-ghost btn-sm" style="cursor: pointer; margin: 0;">
                    ${photoUploaded ? '🔄 Replace Photo' : '📸 Upload Photo'}
                </label>
                <input type="file" id="photo-upload-${result.screening_id}" accept="image/jpeg,image/jpg,image/png,image/webp" style="display:none;"
                    onchange="uploadReferencePhoto('${result.screening_id}', this, ${index})">
                ${photoUploaded ? '<span style="color: #10b981; font-size: 12px;">✅ Face verify ON</span>' : '<span style="color: #f59e0b; font-size: 12px;">⚠️ No photo</span>'}
            `;
        }
        
        return `
            <tr>
                <td>${result.fileName}</td>
                <td><span class="score-badge ${statusClass}">${scorePercent}%</span></td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td><span class="recommendation-badge ${result.recommendation_action || result.recommendation}">${result.recommendation_action || result.recommendation}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                        <button class="btn-outline btn-sm" onclick="viewResultDetail(${index})">View Details</button>
                        ${actionButtons}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    resultsDiv.style.display = 'block';
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

// Delete Screening Result
async function deleteScreeningResult(screeningId, index) {
    if (!confirm('Are you sure you want to delete this screening result?')) {
        return;
    }
    
    try {
        await apiCall(`/screening-results/${screeningId}`, { method: 'DELETE' });
        
        // Remove from batchResults
        batchResults.splice(index, 1);
        
        // Refresh table
        if (batchResults.length > 0) {
            showBatchResults();
        } else {
            closeBatchResults();
        }
        
        showToast('Screening result deleted successfully', 'success');
    } catch (error) {
        console.error('Failed to delete screening result:', error);
        showToast('Failed to delete screening result', 'error');
    }
}

// Send Interview Invitation (Simplified - No Call)
async function sendInvitation(screeningId) {
    try {
        showToast('Sending invitation to candidate...', 'info');
        
        // Call simplified proceed endpoint
        const result = await apiCall(`/screening-results/${screeningId}/proceed`, {
            method: 'POST'
        });
        
        // Show success modal with invitation details
        showInvitationSuccessModal(result);
        
        // Reload screening results to update status
        loadScreeningResults();
        
    } catch (error) {
        console.error('Failed to send invitation:', error);
        showToast(error.message || 'Failed to send invitation', 'error');
    }
}

// Upload Reference Photo for Face Verification
async function uploadReferencePhoto(screeningId, inputEl, index) {
    const file = inputEl.files[0];
    if (!file) return;

    try {
        showToast('Uploading reference photo...', 'info');

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`/api/screening-results/${screeningId}/upload-reference-photo`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload failed');
        }

        // Mark face_verification_enabled in local batchResults
        if (batchResults[index]) {
            batchResults[index].face_verification_enabled = true;
        }

        showToast('Reference photo uploaded! Face verification enabled.', 'success');
        showBatchResults();

    } catch (error) {
        console.error('Photo upload error:', error);
        showToast(error.message || 'Failed to upload photo', 'error');
    }

    // Reset input so same file can be re-uploaded if needed
    inputEl.value = '';
}

// Show Invitation Success Modal
function showInvitationSuccessModal(result) {
    const modal = document.createElement('div');
    modal.className = 'jd-modal';
    modal.innerHTML = `
        <div class="jd-modal-content" style="max-width: 600px;">
            <div class="jd-modal-header" style="background: #10b981; color: white;">
                <h2>✅ Invitation Email Sent!</h2>
                <button class="btn-ghost" onclick="this.closest('.jd-modal').remove()" style="color: white;">✕</button>
            </div>
            <div class="jd-modal-body">
                <div class="jd-section" style="background: #f0fdf4; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 1.5rem;">
                    <p style="margin: 0; color: #065f46;">
                        <strong>📧 Email Sent Successfully!</strong><br>
                        The candidate will receive an email with the invitation code and interview details.
                    </p>
                </div>
                
                <div class="jd-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 12px; text-align: center; margin-bottom: 1.5rem;">
                    <h3 style="color: white; margin-bottom: 0.5rem;">Invitation Code</h3>
                    <p style="font-size: 2.5rem; font-weight: bold; letter-spacing: 0.3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">${result.invitation_code}</p>
                    <button class="btn-ghost" onclick="navigator.clipboard.writeText('${result.invitation_code}'); showToast('Code copied!', 'success')" style="margin-top: 1rem; background: rgba(255,255,255,0.2); color: white;">
                        📋 Copy Code
                    </button>
                </div>
                
                <div class="jd-section">
                    <h4>Candidate Details</h4>
                    <p><strong>Name:</strong> ${result.candidate_name}</p>
                    <p><strong>Email:</strong> ${result.candidate_email}</p>
                    <p><strong>Position:</strong> ${result.jd_title}</p>
                    <p><strong>Valid Until:</strong> ${new Date(result.expires_at).toLocaleDateString()} (7 days)</p>
                </div>
                
                <div class="jd-section" style="background: #eff6ff; padding: 1rem; border-radius: 8px;">
                    <p style="margin: 0; color: #1e40af;">
                        <strong>📝 Next Steps:</strong><br>
                        1. ✅ Candidate receives email with code<br>
                        2. 🌐 They visit the candidate portal<br>
                        3. 🔑 Enter the invitation code<br>
                        4. 🎥 Complete the AI video interview<br>
                        5. 📊 You receive analysis in Interview History<br>
                        6. ☎️ HR follows up based on results
                    </p>
                </div>
                
                <div class="form-actions" style="margin-top: 1.5rem;">
                    <button class="btn-primary" onclick="this.closest('.jd-modal').remove()" style="width: 100%;">Done</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    showToast('Invitation sent successfully!', 'success');
}

// Remove unused call-related functions
// (checkCallStatus, makeConfirmationCall, proceedWithInvitation, showSuccessModal, showRejectionModal)

// Toggle Batch Results
function toggleBatchResults() {
    const batchResults = document.getElementById('batch-results');
    const resultsBody = document.querySelector('.results-table-container');
    const toggleBtn = document.getElementById('toggle-results-btn');
    const toggleIcon = document.getElementById('toggle-icon');
    
    if (!batchResults || !resultsBody) return;
    
    const isCollapsed = resultsBody.style.display === 'none';
    
    if (isCollapsed) {
        resultsBody.style.display = 'block';
        toggleIcon.textContent = '▼';
        toggleBtn.setAttribute('aria-expanded', 'true');
    } else {
        resultsBody.style.display = 'none';
        toggleIcon.textContent = '▶';
        toggleBtn.setAttribute('aria-expanded', 'false');
    }
}

// View Result Detail
async function viewResultDetail(index) {
    const result = batchResults[index];
    
    if (result.status === 'error') {
        showToast(`Error: ${result.error}`, 'error');
        return;
    }
    
    // If we only have summary data, fetch full details
    let fullResult = result;
    if (result.screening_id && !result.detailed_explanation) {
        try {
            fullResult = await apiCall(`/screening-results/${result.screening_id}`);
            // Merge with existing result
            fullResult = { ...result, ...fullResult };
        } catch (error) {
            console.error('Failed to fetch full screening details:', error);
            fullResult = result;
        }
    }
    
    // Helper function to format recommendation action
    const formatRecommendation = (action) => {
        const map = {
            'proceed': '✅ Proceed with Interview',
            'maybe': '⚠️ Further Review Needed',
            'reject': '❌ Not Recommended'
        };
        return map[action] || action;
    };
    
    // Helper function to format match type
    const formatMatchType = (type) => {
        const map = {
            'strong_match': 'Strong Match',
            'moderate_match': 'Moderate Match',
            'weak_match': 'Weak Match'
        };
        return map[type] || type;
    };
    
    const modal = document.createElement('div');
    modal.className = 'jd-modal';
    modal.innerHTML = `
        <div class="jd-modal-content" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
            <div class="jd-modal-header">
                <h2>📄 ${fullResult.fileName || fullResult.file_name}</h2>
                <button class="btn-ghost" onclick="this.closest('.jd-modal').remove()">✕</button>
            </div>
            <div class="jd-modal-body">
                <!-- Score Overview -->
                <div class="jd-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; text-align: center;">
                        <div>
                            <p style="opacity: 0.9; margin-bottom: 0.5rem; font-size: 0.9rem;">Overall Match Score</p>
                            <p style="font-size: 2rem; font-weight: bold; margin: 0;">${Math.round(fullResult.overall_match_score || 0)}%</p>
                        </div>
                        <div>
                            <p style="opacity: 0.9; margin-bottom: 0.5rem; font-size: 0.9rem;">Recommendation</p>
                            <p style="font-size: 1.2rem; font-weight: bold; margin: 0;">${formatMatchType(fullResult.final_recommendation || 'N/A')}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Detailed Explanation -->
                <div class="jd-section">
                    <h4>📋 Detailed Analysis</h4>
                    <p style="line-height: 1.8; color: var(--foreground);">${fullResult.detailed_explanation || fullResult.analysis || 'No detailed explanation available.'}</p>
                </div>
                
                <!-- Skills Analysis -->
                ${fullResult.skills_analysis ? `
                <div class="jd-section">
                    <h4>🎯 Skills Analysis</h4>
                    <p><strong>Skills Match:</strong> ${Math.round(fullResult.skills_analysis.skills_match_percentage || 0)}%</p>
                    
                    ${fullResult.skills_analysis.required_skills_matched && fullResult.skills_analysis.required_skills_matched.length > 0 ? `
                    <div style="margin-top: 1rem;">
                        <p style="color: #10b981; font-weight: 600; margin-bottom: 0.5rem;">✅ Skills Matched:</p>
                        <div class="skills-tags">
                            ${fullResult.skills_analysis.required_skills_matched.map(skill => 
                                `<span class="skill-tag" style="background: #d1fae5; color: #065f46;">${skill}</span>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${fullResult.skills_analysis.required_skills_missing && fullResult.skills_analysis.required_skills_missing.length > 0 ? `
                    <div style="margin-top: 1rem;">
                        <p style="color: #ef4444; font-weight: 600; margin-bottom: 0.5rem;">❌ Skills Missing:</p>
                        <div class="skills-tags">
                            ${fullResult.skills_analysis.required_skills_missing.map(skill => 
                                `<span class="skill-tag" style="background: #fee2e2; color: #991b1b;">${skill}</span>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${fullResult.skills_analysis.additional_relevant_skills && fullResult.skills_analysis.additional_relevant_skills.length > 0 ? `
                    <div style="margin-top: 1rem;">
                        <p style="color: #3b82f6; font-weight: 600; margin-bottom: 0.5rem;">➕ Additional Skills:</p>
                        <div class="skills-tags">
                            ${fullResult.skills_analysis.additional_relevant_skills.map(skill => 
                                `<span class="skill-tag" style="background: #dbeafe; color: #1e40af;">${skill}</span>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
                
                <!-- Experience Analysis -->
                ${fullResult.experience_analysis ? `
                <div class="jd-section">
                    <h4>💼 Experience Analysis</h4>
                    <p><strong>Match Level:</strong> <span style="text-transform: capitalize;">${fullResult.experience_analysis.experience_match || 'N/A'}</span></p>
                    <p style="margin-top: 0.5rem;">${fullResult.experience_analysis.explanation || ''}</p>
                    ${fullResult.experience_analysis.relevant_projects && fullResult.experience_analysis.relevant_projects.length > 0 ? `
                    <div style="margin-top: 1rem;">
                        <p style="font-weight: 600; margin-bottom: 0.5rem;">Relevant Projects:</p>
                        <ul style="margin-left: 1.5rem;">
                            ${fullResult.experience_analysis.relevant_projects.map(proj => `<li>${proj}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
                
                <!-- Strengths & Weaknesses -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                    ${fullResult.strengths && fullResult.strengths.length > 0 ? `
                    <div class="jd-section" style="background: #f0fdf4; border-left: 4px solid #10b981;">
                        <h4 style="color: #10b981;">💪 Strengths</h4>
                        <ul style="margin-left: 1.5rem; line-height: 1.8;">
                            ${fullResult.strengths.map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    
                    ${fullResult.weaknesses && fullResult.weaknesses.length > 0 ? `
                    <div class="jd-section" style="background: #fef2f2; border-left: 4px solid #ef4444;">
                        <h4 style="color: #ef4444;">⚠️ Concerns</h4>
                        <ul style="margin-left: 1.5rem; line-height: 1.8;">
                            ${fullResult.weaknesses.map(w => `<li>${w}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                </div>
                
                <!-- Key Highlights -->
                ${fullResult.key_highlights && fullResult.key_highlights.length > 0 ? `
                <div class="jd-section">
                    <h4>⭐ Key Highlights</h4>
                    <ul style="margin-left: 1.5rem; line-height: 1.8;">
                        ${fullResult.key_highlights.map(h => `<li>${h}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                <!-- Interview Focus Areas -->
                ${fullResult.interview_focus_areas && fullResult.interview_focus_areas.length > 0 ? `
                <div class="jd-section" style="background: #eff6ff; border-left: 4px solid #3b82f6;">
                    <h4 style="color: #3b82f6;">🎤 Interview Focus Areas</h4>
                    <ul style="margin-left: 1.5rem; line-height: 1.8;">
                        ${fullResult.interview_focus_areas.map(a => `<li>${a}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                <!-- Additional Factors -->
                <div class="jd-section">
                    <h4>📊 Additional Factors</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                        ${fullResult.location_match ? `
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Location</p>
                            <p style="text-transform: capitalize;">${fullResult.location_match.replace('_', ' ')}</p>
                        </div>
                        ` : ''}
                        ${fullResult.salary_expectation_alignment ? `
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Salary Alignment</p>
                            <p style="text-transform: capitalize;">${fullResult.salary_expectation_alignment.replace('_', ' ')}</p>
                        </div>
                        ` : ''}
                        ${fullResult.education_analysis ? `
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Education</p>
                            <p style="text-transform: capitalize;">${fullResult.education_analysis.education_match || 'N/A'}</p>
                        </div>
                        ` : ''}
                        ${typeof fullResult.notice_period_concern !== 'undefined' ? `
                        <div>
                            <p style="font-weight: 600; margin-bottom: 0.3rem;">Notice Period</p>
                            <p>${fullResult.notice_period_concern ? '⚠️ Concern' : '✅ Acceptable'}</p>
                        </div>
                        ` : ''}
                    </div>
                </div>
                
                <!-- Final Recommendation -->
                <div class="jd-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 1.5rem;">
                    <h4 style="color: white; margin-bottom: 1rem;">Final Recommendation</h4>
                    <p style="font-size: 1.5rem; font-weight: bold; margin: 0;">
                        ${formatRecommendation(fullResult.recommendation_action || fullResult.recommendation)}
                    </p>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Edit JD
let editingJdId = null;

async function editJD(jdId) {
    try {
        const jd = await apiCall(`/jds/${jdId}`);
        editingJdId = jdId;
        
        // Switch to JD management tab
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const selectedTab = document.getElementById('tab-jd-management');
        if (selectedTab) {
            selectedTab.classList.add('active');
        }
        
        // Activate the JD management tab button
        const jdManagementBtn = Array.from(document.querySelectorAll('.tab-btn')).find(
            btn => btn.textContent.includes('Manage JDs')
        );
        if (jdManagementBtn) {
            jdManagementBtn.classList.add('active');
        }
        
        // Populate form
        document.getElementById('jd-title').value = jd.title;
        document.getElementById('jd-description').value = jd.description;
        document.getElementById('jd-requirements').value = jd.requirements;
        document.getElementById('jd-skills').value = jd.skills.join(', ');
        document.getElementById('jd-location').value = jd.location || '';
        document.getElementById('jd-experience').value = jd.experience_required || '';
        document.getElementById('jd-salary').value = jd.salary_range || '';
        document.getElementById('jd-notice').value = jd.notice_period_acceptable || '';
        
        // Show form directly
        const form = document.getElementById('jd-form');
        const listContainer = document.getElementById('jd-list-container');
        form.style.display = 'block';
        listContainer.style.display = 'none';
        
        // Change form title
        form.querySelector('h3').textContent = 'Edit Job Description';
    } catch (error) {
        console.error('Failed to load JD:', error);
        showToast('Failed to load job description', 'error');
    }
}

// View JD in Modal
async function viewJDModal(jdId) {
    try {
        const jd = await apiCall(`/jds/${jdId}`);
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'jd-modal';
        modal.innerHTML = `
            <div class="jd-modal-content">
                <div class="jd-modal-header">
                    <h2>${jd.title}</h2>
                    <button class="btn-ghost" onclick="this.closest('.jd-modal').remove()">✕</button>
                </div>
                <div class="jd-modal-body">
                    ${jd.location ? `<div class="jd-section">
                        <h4>Location</h4>
                        <p>${jd.location}</p>
                    </div>` : ''}
                    ${jd.experience_required ? `<div class="jd-section">
                        <h4>Experience Required</h4>
                        <p>${jd.experience_required}</p>
                    </div>` : ''}
                    ${jd.salary_range ? `<div class="jd-section">
                        <h4>Salary Range</h4>
                        <p>${jd.salary_range}</p>
                    </div>` : ''}
                    ${jd.notice_period_acceptable ? `<div class="jd-section">
                        <h4>Notice Period Acceptable</h4>
                        <p>${jd.notice_period_acceptable}</p>
                    </div>` : ''}
                    <div class="jd-section">
                        <h4>Description</h4>
                        <p>${jd.description}</p>
                    </div>
                    <div class="jd-section">
                        <h4>Requirements</h4>
                        <p>${jd.requirements}</p>
                    </div>
                    <div class="jd-section">
                        <h4>Skills Required</h4>
                        <div class="skills-tags">
                            ${jd.skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
                        </div>
                    </div>
                    <div class="jd-section">
                        <p class="text-muted">Created: ${new Date(jd.created_at).toLocaleDateString()}</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    } catch (error) {
        console.error('Failed to load JD:', error);
        showToast('Failed to load job description', 'error');
    }
}

// Load Stats
async function loadStats() {
    try {
        const [candidates, interviews] = await Promise.all([
            apiCall('/candidates'),
            apiCall('/interviews')
        ]);
        
        const completedCount = interviews.filter(i => i.status === 'completed').length;
        const inProgressCount = interviews.filter(i => i.status === 'in_progress').length;
        
        document.getElementById('total-candidates').textContent = candidates.length;
        document.getElementById('completed-interviews').textContent = completedCount;
        document.getElementById('inprogress-interviews').textContent = inProgressCount;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadJobDescriptions();
    loadStats();
    
    // Load existing screening results
    loadScreeningResults();
    
    const jdSelect = document.getElementById('jd-select');
    if (jdSelect) {
        jdSelect.addEventListener('change', checkFormValidity);
    }
});
