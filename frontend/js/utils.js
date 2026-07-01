// API Base URL
const API_BASE_URL = 'http://localhost:8000/api';

// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Navigation
function navigateTo(path) {
    window.location.href = path;
}

// Mobile Menu Toggle
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    const icon = document.getElementById('menu-icon');
    if (menu) {
        menu.classList.toggle('active');
        icon.textContent = menu.classList.contains('active') ? '✕' : '☰';
    }
}

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message || 'An error occurred', 'error');
        throw error;
    }
}

// File Upload Helper
async function uploadFile(endpoint, file, additionalData = {}) {
    const formData = new FormData();
    
    // Handle blob or file
    if (file instanceof Blob) {
        if (endpoint.includes('/media/video')) {
            formData.append('video_file', file, 'video.webm');
        } else if (endpoint.includes('/media/audio')) {
            formData.append('audio_file', file, 'audio.wav');
        } else if (endpoint.includes('/media/image')) {
            formData.append('image_file', file, 'image.jpg');
        } else {
            formData.append('file', file);
        }
    } else {
        formData.append('file', file);
    }
    
    Object.keys(additionalData).forEach(key => {
        if (additionalData[key] !== null && additionalData[key] !== undefined) {
            formData.append(key, additionalData[key]);
        }
    });
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Upload Error:', error);
        showToast(error.message || 'Upload failed', 'error');
        throw error;
    }
}

// Format File Size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Format Time
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Set Current Year
document.addEventListener('DOMContentLoaded', () => {
    const yearElement = document.getElementById('current-year');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
});
