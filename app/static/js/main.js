/**
 * 群防群治智慧警务平台 - 主JavaScript
 * 拍照、定位、动画、实时追踪
 */

document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
    initPopovers();
    autoHideAlerts();
    initFormValidation();
    initScrollAnimations();
    initCameraButtons();
});

// ==================== UI初始化 ====================

function initTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el) {
        return new bootstrap.Tooltip(el);
    });
}

function initPopovers() {
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function(el) {
        return new bootstrap.Popover(el);
    });
}

function autoHideAlerts() {
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
}

function initFormValidation() {
    document.querySelectorAll('.needs-validation').forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// 滚动动画
function initScrollAnimations() {
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.animate-on-scroll, .feature-card, .reward-card, .task-card').forEach(function(el) {
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });
}

// ==================== 拍照功能 ====================

function initCameraButtons() {
    document.querySelectorAll('.btn-camera').forEach(function(btn) {
        btn.addEventListener('click', openCamera);
    });
}

function openCamera(event) {
    event.preventDefault();
    var targetInput = document.getElementById(btn.dataset.target || 'camera-input');

    // 创建拍照模态框
    var modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'camera-modal';
    modal.innerHTML = '<div class="modal-dialog modal-lg"><div class="modal-content">' +
        '<div class="modal-header"><h5 class="modal-title"><i class="bi bi-camera me-2"></i>拍照上传</h5>' +
        '<button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>' +
        '<div class="modal-body text-center">' +
        '<div class="camera-container mb-3">' +
        '<video id="camera-preview" autoplay playsinline style="width:100%;max-width:640px;border-radius:10px;"></video>' +
        '<canvas id="camera-canvas" style="display:none;"></canvas>' +
        '</div>' +
        '<div class="btn-group">' +
        '<button class="btn btn-primary" id="btn-capture"><i class="bi bi-camera me-1"></i>拍照</button>' +
        '<button class="btn btn-outline-secondary" id="btn-switch-camera"><i class="bi bi-arrow-repeat me-1"></i>切换摄像头</button>' +
        '</div>' +
        '<div id="photo-preview" class="mt-3" style="display:none;">' +
        '<img id="captured-photo" style="max-width:640px;max-height:400px;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">' +
        '<div class="mt-2"><button class="btn btn-success" id="btn-use-photo"><i class="bi bi-check-lg me-1"></i>使用照片</button>' +
        '<button class="btn btn-outline-danger ms-2" id="btn-retake"><i class="bi bi-arrow-repeat me-1"></i>重拍</button></div>' +
        '</div></div></div></div>';

    document.body.appendChild(modal);
    var bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    var stream = null;
    var facingMode = 'environment';

    function startCamera() {
        if (stream) {
            stream.getTracks().forEach(function(t) { t.stop(); });
        }
        navigator.mediaDevices.getUserMedia({ video: { facingMode: facingMode, width: { ideal: 1280 }, height: { ideal: 720 } } })
            .then(function(s) {
                stream = s;
                document.getElementById('camera-preview').srcObject = s;
            })
            .catch(function() {
                alert('无法访问摄像头，请检查权限设置');
            });
    }

    startCamera();

    document.getElementById('btn-capture').addEventListener('click', function() {
        var video = document.getElementById('camera-preview');
        var canvas = document.getElementById('camera-canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        var dataUrl = canvas.toDataURL('image/jpeg', 0.85);

        document.getElementById('captured-photo').src = dataUrl;
        document.getElementById('camera-preview').style.display = 'none';
        document.getElementById('photo-preview').style.display = 'block';
        document.getElementById('btn-capture').style.display = 'none';
        document.getElementById('btn-switch-camera').style.display = 'none';
    });

    document.getElementById('btn-switch-camera').addEventListener('click', function() {
        facingMode = facingMode === 'environment' ? 'user' : 'environment';
        startCamera();
    });

    document.getElementById('btn-retake').addEventListener('click', function() {
        document.getElementById('camera-preview').style.display = '';
        document.getElementById('photo-preview').style.display = 'none';
        document.getElementById('btn-capture').style.display = '';
        document.getElementById('btn-switch-camera').style.display = '';
    });

    document.getElementById('btn-use-photo').addEventListener('click', function() {
        var dataUrl = document.getElementById('captured-photo').src;
        fetch(dataUrl)
            .then(function(res) { return res.blob(); })
            .then(function(blob) {
                var file = new File([blob], 'camera_' + Date.now() + '.jpg', { type: 'image/jpeg' });
                var dt = new DataTransfer();
                dt.items.add(file);
                var input = document.getElementById(targetInput);
                if (input) {
                    input.files = dt.files;
                    previewImage(input, input.dataset.preview || 'image-preview');
                }
            });
        if (stream) stream.getTracks().forEach(function(t) { t.stop(); });
        bsModal.hide();
        setTimeout(function() { modal.remove(); }, 300);
    });

    modal.addEventListener('hidden.bs.modal', function() {
        if (stream) stream.getTracks().forEach(function(t) { t.stop(); });
        modal.remove();
    });
}

// ==================== 实时定位追踪 ====================

var locationWatcher = null;
var locationUpdateInterval = null;

function startLocationTracking(options) {
    options = options || {};
    var updateUrl = options.updateUrl || '/api/user/location';
    var interval = options.interval || 30000; // 默认30秒上报一次
    var onPosition = options.onPosition || function() {};

    if (!navigator.geolocation) {
        console.warn('浏览器不支持地理定位');
        return;
    }

    // 持续追踪位置
    locationWatcher = navigator.geolocation.watchPosition(
        function(position) {
            var data = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                accuracy: position.coords.accuracy,
                timestamp: new Date().toISOString()
            };
            onPosition(data);
        },
        function(error) {
            console.warn('定位失败:', error.message);
        },
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 }
    );

    // 定时上报到服务器
    locationUpdateInterval = setInterval(function() {
        getCurrentPosition(function(result) {
            if (result.success) {
                fetch(updateUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lat: result.lat, lng: result.lng })
                });
            }
        });
    }, interval);
}

function stopLocationTracking() {
    if (locationWatcher !== null) {
        navigator.geolocation.clearWatch(locationWatcher);
        locationWatcher = null;
    }
    if (locationUpdateInterval !== null) {
        clearInterval(locationUpdateInterval);
        locationUpdateInterval = null;
    }
}

function getCurrentPosition(callback) {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                callback({
                    success: true,
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                });
            },
            function(error) {
                callback({ success: false, error: error.message });
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    } else {
        callback({ success: false, error: '浏览器不支持地理定位' });
    }
}

// 填充位置字段
function fillLocationFields(latField, lngField, locationField) {
    getCurrentPosition(function(result) {
        if (result.success) {
            if (latField) document.querySelector(latField).value = result.lat;
            if (lngField) document.querySelector(lngField).value = result.lng;

            // 调用反向地理编码获取地址
            if (locationField) {
                fetch('/api/geocode?lat=' + result.lat + '&lng=' + result.lng)
                    .then(function(r) { return r.json(); })
                    .then(function(res) {
                        if (res.success && res.address) {
                            document.querySelector(locationField).value = res.address;
                        }
                    });
            }
        } else {
            alert('获取位置失败: ' + (result.error || '未知错误'));
        }
    });
}

// ==================== AJAX封装 ====================

function ajaxRequest(url, options) {
    options = options || {};
    var method = options.method || 'GET';
    var data = options.data || null;
    var headers = options.headers || {};

    return fetch(url, { method: method, headers: headers, body: data })
        .then(function(response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        })
        .then(function(data) {
            if (options.success) options.success(data);
            return data;
        })
        .catch(function(error) {
            if (options.error) options.error(error);
            throw error;
        });
}

// ==================== 提示消息 ====================

function showToast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.container') || document.body;
    var toast = document.createElement('div');
    toast.className = 'alert alert-' + type + ' alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    container.prepend(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

function showLoading(element, text) {
    text = text || '加载中...';
    element.innerHTML = '<div class="text-center py-4"><div class="loading"></div><p class="mt-2 text-muted">' + text + '</p></div>';
}

function showError(message) {
    showToast('<i class="bi bi-exclamation-circle me-1"></i>' + message, 'danger');
}

function showSuccess(message) {
    showToast('<i class="bi bi-check-circle me-1"></i>' + message, 'success');
}

// ==================== 工具函数 ====================

function confirmDialog(message, callback) {
    if (confirm(message)) callback();
}

function formatDate(dateString) {
    var date = new Date(dateString);
    var y = date.getFullYear();
    var m = String(date.getMonth() + 1).padStart(2, '0');
    var d = String(date.getDate()).padStart(2, '0');
    var h = String(date.getHours()).padStart(2, '0');
    var min = String(date.getMinutes()).padStart(2, '0');
    return y + '-' + m + '-' + d + ' ' + h + ':' + min;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showSuccess('已复制到剪贴板');
    });
}

function debounce(func, wait) {
    var timeout;
    return function() {
        var ctx = this, args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() { func.apply(ctx, args); }, wait);
    };
}

function throttle(func, limit) {
    var inThrottle;
    return function() {
        var ctx = this, args = arguments;
        if (!inThrottle) {
            func.apply(ctx, args);
            inThrottle = true;
            setTimeout(function() { inThrottle = false; }, limit);
        }
    };
}

function previewImage(input, previewId) {
    var preview = document.getElementById(previewId);
    if (!preview) return;
    preview.innerHTML = '';

    if (input.files) {
        Array.from(input.files).forEach(function(file) {
            if (file.type.startsWith('image/')) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var img = document.createElement('img');
                    img.src = e.target.result;
                    img.className = 'img-thumbnail me-2 mb-2';
                    img.style.cssText = 'max-width:150px; max-height:150px; border-radius:8px;';
                    preview.appendChild(img);
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

function countdown(element, seconds, callback) {
    var timer = setInterval(function() {
        element.textContent = seconds;
        seconds--;
        if (seconds < 0) {
            clearInterval(timer);
            if (callback) callback();
        }
    }, 1000);
}

// ==================== 导出全局API ====================

window.PolicePlatform = {
    getCurrentPosition: getCurrentPosition,
    startLocationTracking: startLocationTracking,
    stopLocationTracking: stopLocationTracking,
    fillLocationFields: fillLocationFields,
    ajaxRequest: ajaxRequest,
    showLoading: showLoading,
    showError: showError,
    showSuccess: showSuccess,
    showToast: showToast,
    confirmDialog: confirmDialog,
    formatDate: formatDate,
    copyToClipboard: copyToClipboard,
    debounce: debounce,
    throttle: throttle,
    previewImage: previewImage,
    countdown: countdown,
    openCamera: openCamera
};
