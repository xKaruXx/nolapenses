/**
 * Main JavaScript for No La Penses! Landing Page
 * Handles all interactive functionality including:
 * - AI mood generation
 * - User mood selection and webhook
 * - Voice recording and processing
 * - Form submission and WhatsApp integration
 * - Scroll animations
 */

// Definir landingApp globalmente para que Alpine.js pueda acceder a él inmediatamente
window.landingApp = function() {
    return {
        // AI state
        aiMood: '',
        aiGreeting: '',
        
        // User mood state
        userMood: '',
        userMoodEmoji: '',
        userMoodResponse: '',
        
        // Voice recording state
        isRecording: false,
        mediaRecorder: null,
        audioChunks: [],
        voiceResponse: '',
        audioResponse: null,
        
        // Form state
        form: {
            nombre: '',
            telefono: '',
            estado_animo: ''
        },
        formSubmitted: false,
        formSuccess: false,
        
        // Browser info for analytics
        browserInfo: {
            name: 'Chrome',
            time: new Date().toLocaleTimeString()
        },
        
        // Initialize the app
        init() {
            try {
                console.log('Inicializando la aplicación...');
                
                // Verificar que CONFIG esté cargado
                if (typeof CONFIG === 'undefined') {
                    console.error('Error: El objeto CONFIG no está definido. Asegúrate de que config.js se cargue antes que main.js');
                    return;
                }
                
                this.setRandomAIMood();
                this.initScrollAnimations();
                this.setupScrollIndicator();
                this.browserInfo.name = this.getBrowserName();
                
                console.log('Aplicación inicializada correctamente');
            } catch (error) {
                console.error('Error durante la inicialización:', error);
            }
        },
        
        // Set a random AI mood on page load
        setRandomAIMood() {
            try {
                console.log('Configurando estado de ánimo aleatorio para la IA...');
                
                if (!CONFIG.aiMoods || !Array.isArray(CONFIG.aiMoods) || CONFIG.aiMoods.length === 0) {
                    console.error('CONFIG.aiMoods no está definido correctamente');
                    this.aiMood = 'alegre';
                    this.aiGreeting = '¡Hola! ¿En qué puedo ayudarte hoy?';
                    return;
                }
                
                const randomIndex = Math.floor(Math.random() * CONFIG.aiMoods.length);
                const selectedMood = CONFIG.aiMoods[randomIndex];
                
                this.aiMood = selectedMood.mood;
                this.aiGreeting = selectedMood.greeting;
                
                console.log('Estado de ánimo de la IA configurado:', this.aiMood);
            } catch (error) {
                console.error('Error al configurar el estado de ánimo de la IA:', error);
                this.aiMood = 'alegre';
                this.aiGreeting = '¡Hola! ¿En qué puedo ayudarte hoy?';
            }
        },
        
        // Handle user mood selection
        setUserMood(mood, emoji) {
            try {
                console.log('Usuario seleccionó estado de ánimo:', mood, emoji);
                
                this.userMood = mood;
                this.userMoodEmoji = emoji;
                
                // Establecer respuesta inicial desde CONFIG si está disponible
                if (CONFIG.userMoodResponses && CONFIG.userMoodResponses[mood]) {
                    this.userMoodResponse = CONFIG.userMoodResponses[mood];
                } else {
                    this.userMoodResponse = 'Gracias por compartir cómo te sentís hoy.';
                }
                
                this.form.estado_animo = mood;
                
                // Send mood data to webhook
                this.sendMoodWebhook(mood);
                
                // Get personalized greeting from webhook
                this.getPersonalizedGreeting(mood);
                
                console.log('Estado de ánimo del usuario actualizado:', this.userMood);
            } catch (error) {
                console.error('Error al establecer el estado de ánimo del usuario:', error);
                this.userMoodResponse = 'Gracias por compartir cómo te sentís hoy.';
            }
        },
        
        // Send user mood to n8n webhook
        sendMoodWebhook(mood) {
            try {
                console.log('Enviando estado de ánimo al webhook:', mood);
                
                // Prepare data for webhook
                const webhookData = {
                    estado: mood,
                    hora: this.browserInfo.time,
                    navegador: this.browserInfo.name
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (!isLocalEnvironment) {
                    // Send data to webhook in production environment
                    fetch(CONFIG.webhooks.userMood, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook:', data);
                    })
                    .catch(error => {
                        console.error('Error al enviar datos al webhook:', error);
                    });
                } else {
                    console.log('Entorno local detectado. Simulando envío al webhook:', webhookData);
                }
            } catch (error) {
                console.error('Error al enviar el estado de ánimo al webhook:', error);
            }
        },
        
        // Get personalized greeting from webhook
        getPersonalizedGreeting(mood) {
            try {
                console.log('Obteniendo saludo personalizado para el estado de ánimo:', mood);
                
                // Show loading state
                this.userMoodResponse = 'Procesando tu estado de ánimo...';
                
                // Prepare data for webhook
                const webhookData = {
                    estado: mood,
                    hora: this.browserInfo.time,
                    navegador: this.browserInfo.name,
                    ai_mood: this.aiMood
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando respuesta del webhook...');
                    
                    // Simulate webhook response locally after a short delay
                    setTimeout(() => {
                        // Simulated personalized greetings based on mood
                        const simulatedResponses = {
                            'Alegre': `¡Qué buena onda que estés re contento! ${this.aiMood === 'alegre' ? 'Yo también estoy re arriba hoy.' : 'Me contagiás tu buena onda.'} ¿Querés que te cuente qué podemos hacer por vos?`,
                            'Creativo': `¡Banco fuerte tu creatividad! ${this.aiMood === 'creativo' ? 'Hoy estamos re inspirados los dos.' : 'Me encanta charlar con gente creativa.'} ¿Te gustaría ver algunos de nuestros proyectos más creativos?`,
                            'Energético': `¡Estás a mil! ${this.aiMood === 'energético' ? 'Yo también estoy re manija hoy.' : 'Se nota que venís con toda la energía.'} Con esa actitud, podemos hacer altas cosas juntos.`,
                            'Curioso': `¡Qué bueno que seas chusma! ${this.aiMood === 'curioso' ? 'Yo también soy re metido.' : 'La curiosidad es clave para descubrir cosas nuevas.'} ¿Querés que te cuente más sobre lo que hacemos?`,
                            'Motivado': `¡Esa es la actitud! ${this.aiMood === 'motivado' ? 'Hoy estamos los dos con todas las pilas.' : 'Se nota que venís con ganas de hacer cosas.'} Vamos a romperla toda con tu proyecto.`
                        };
                        
                        // Update the response with simulated greeting
                        this.userMoodResponse = simulatedResponses[mood] || CONFIG.userMoodResponses[mood];
                        console.log('Respuesta simulada:', this.userMoodResponse);
                    }, 1500);
                } else {
                    // In production, make an actual API call
                    fetch(CONFIG.webhooks.userMood, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook:', data);
                        
                        // Update the greeting with the response from the webhook
                        if (data && data.greeting) {
                            this.userMoodResponse = data.greeting;
                        } else {
                            // Fallback to default response if webhook doesn't return a greeting
                            this.userMoodResponse = CONFIG.userMoodResponses[mood];
                        }
                    })
                    .catch(error => {
                        console.error('Error al obtener saludo personalizado:', error);
                        // Fallback to default response on error
                        this.userMoodResponse = CONFIG.userMoodResponses[mood];
                    });
                }
            } catch (error) {
                console.error('Error al obtener el saludo personalizado:', error);
                this.userMoodResponse = CONFIG.userMoodResponses[mood] || 'Gracias por compartir cómo te sentís hoy.';
            }
        },
        
        // Toggle voice recording
        toggleRecording() {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        },
        
        // Start voice recording
        startRecording() {
            try {
                console.log('Iniciando grabación de voz...');
                
                this.isRecording = true;
                this.audioChunks = [];
                
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        this.mediaRecorder = new MediaRecorder(stream);
                        
                        this.mediaRecorder.addEventListener('dataavailable', event => {
                            this.audioChunks.push(event.data);
                        });
                        
                        this.mediaRecorder.addEventListener('stop', () => {
                            const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                            const reader = new FileReader();
                            
                            reader.readAsDataURL(audioBlob);
                            reader.onloadend = () => {
                                const base64data = reader.result.split(',')[1];
                                this.sendAudioWebhook(base64data);
                            };
                        });
                        
                        this.mediaRecorder.start();
                        
                        console.log('Grabación iniciada correctamente');
                    })
                    .catch(error => {
                        console.error('Error al acceder al micrófono:', error);
                        alert('No se pudo acceder al micrófono. Por favor, verifica los permisos del navegador.');
                        this.isRecording = false;
                    });
            } catch (error) {
                console.error('Error al iniciar la grabación:', error);
                this.isRecording = false;
            }
        },
        
        // Stop voice recording
        stopRecording() {
            try {
                console.log('Deteniendo grabación de voz...');
                
                if (this.mediaRecorder && this.isRecording) {
                    this.mediaRecorder.stop();
                    this.isRecording = false;
                    
                    // Stop all audio tracks
                    this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    
                    console.log('Grabación detenida correctamente');
                }
            } catch (error) {
                console.error('Error al detener la grabación:', error);
                this.isRecording = false;
            }
        },
        
        // Send recorded audio to webhook
        sendAudioWebhook(audioBase64) {
            try {
                console.log('Enviando audio al webhook...');
                
                // Show loading state
                this.voiceResponse = 'Procesando tu mensaje de voz...';
                
                // Prepare data for webhook
                const webhookData = {
                    audio: audioBase64,
                    estado_animo: this.userMood,
                    navegador: this.browserInfo.name
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando respuesta del webhook de audio...');
                    
                    // Simulate webhook response locally after a short delay
                    setTimeout(() => {
                        this.voiceResponse = '¡Gracias por tu mensaje! Entendimos que necesitas ayuda con tu proyecto digital. Nuestro equipo puede ayudarte a crear una solución personalizada. ¿Te gustaría que te contactemos por WhatsApp para darte más detalles?';
                        console.log('Respuesta simulada para el audio:', this.voiceResponse);
                    }, 2000);
                } else {
                    // In production, make an actual API call
                    fetch(CONFIG.webhooks.audioReceived, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook de audio:', data);
                        
                        // Update with the response from the webhook
                        if (data && data.transcription) {
                            this.voiceResponse = data.transcription;
                        }
                        
                        // Set audio response if available
                        if (data && data.audio_url) {
                            this.audioResponse = data.audio_url;
                        }
                    })
                    .catch(error => {
                        console.error('Error al enviar audio al webhook:', error);
                        this.voiceResponse = 'Lo sentimos, hubo un error al procesar tu mensaje de voz. Por favor, intenta nuevamente.';
                    });
                }
            } catch (error) {
                console.error('Error al enviar el audio al webhook:', error);
                this.voiceResponse = 'Lo sentimos, hubo un error al procesar tu mensaje de voz. Por favor, intenta nuevamente.';
            }
        },
        
        // Submit contact form
        submitForm() {
            try {
                console.log('Enviando formulario de contacto...');
                
                // Validate form
                if (!this.form.nombre || !this.form.telefono) {
                    alert('Por favor, completá todos los campos del formulario.');
                    return;
                }
                
                this.formSubmitted = true;
                
                // Prepare data for webhook
                const webhookData = {
                    nombre: this.form.nombre,
                    telefono: this.form.telefono,
                    estado_animo: this.form.estado_animo,
                    navegador: this.browserInfo.name,
                    hora: this.browserInfo.time
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando envío del formulario:', webhookData);
                    
                    // Simulate webhook response locally after a short delay
                    setTimeout(() => {
                        this.formSuccess = true;
                        console.log('Formulario enviado correctamente (simulado)');
                    }, 1500);
                } else {
                    // In production, make an actual API call
                    fetch(CONFIG.webhooks.newLead, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook de formulario:', data);
                        this.formSuccess = true;
                    })
                    .catch(error => {
                        console.error('Error al enviar formulario:', error);
                        alert('Hubo un error al enviar el formulario. Por favor, intenta nuevamente.');
                        this.formSubmitted = false;
                    });
                }
            } catch (error) {
                console.error('Error al enviar el formulario:', error);
                alert('Hubo un error al enviar el formulario. Por favor, intenta nuevamente.');
                this.formSubmitted = false;
            }
        },
        
        // Initialize scroll animations
        initScrollAnimations() {
            try {
                console.log('Inicializando animaciones de desplazamiento...');
                
                // Add reveal class to elements
                const revealElements = document.querySelectorAll('section');
                
                // Create intersection observer
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('active');
                        }
                    });
                }, {
                    threshold: 0.1
                });
                
                // Observe each section
                revealElements.forEach(element => {
                    element.classList.add('reveal');
                    observer.observe(element);
                });
                
                console.log('Animaciones de desplazamiento inicializadas correctamente');
            } catch (error) {
                console.error('Error al inicializar las animaciones de desplazamiento:', error);
            }
        },
        
        // Setup scroll indicator functionality
        setupScrollIndicator() {
            try {
                console.log('Configurando indicador de desplazamiento...');
                
                // Get the scroll indicator element
                const scrollIndicator = document.querySelector('.absolute.bottom-8.left-1\\/2');
                if (!scrollIndicator) {
                    console.error('No se encontró el indicador de desplazamiento');
                    return;
                }
                
                // Make it clickable
                scrollIndicator.style.cursor = 'pointer';
                
                // Add click event listener
                scrollIndicator.addEventListener('click', () => {
                    // Get the first section after the header
                    const nextSection = document.querySelector('header + section');
                    if (nextSection) {
                        // Scroll to the next section smoothly
                        nextSection.scrollIntoView({ behavior: 'smooth' });
                    }
                });
                
                console.log('Indicador de desplazamiento configurado correctamente');
            } catch (error) {
                console.error('Error al configurar el indicador de desplazamiento:', error);
            }
        },
        
        // Get browser name for analytics
        getBrowserName() {
            try {
                const userAgent = navigator.userAgent;
                let browserName;
                
                if (userAgent.match(/chrome|chromium|crios/i)) {
                    browserName = "Chrome";
                } else if (userAgent.match(/firefox|fxios/i)) {
                    browserName = "Firefox";
                } else if (userAgent.match(/safari/i)) {
                    browserName = "Safari";
                } else if (userAgent.match(/opr\//i)) {
                    browserName = "Opera";
                } else if (userAgent.match(/edg/i)) {
                    browserName = "Edge";
                } else {
                    browserName = "Unknown";
                }
                
                return browserName;
            } catch (error) {
                console.error('Error al obtener el nombre del navegador:', error);
                return 'Unknown';
            }
        }
    };
};

// Log when the script is loaded
console.log('main.js cargado correctamente');

// Mock API response for demo purposes in local environment
(function(originalFetch) {
    window.fetch = function(url, options) {
        return new Promise((resolve, reject) => {
            // Check if this is a webhook call
            if (url.includes('webhook')) {
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Simulando respuesta de API para:', url);
                    
                    // Simulate successful response
                    setTimeout(() => {
                        if (url.includes('audio-recibido')) {
                            // Simulate audio processing response
                            resolve({
                                json: () => Promise.resolve({
                                    transcription: '¡Gracias por tu mensaje! Entendimos que necesitas ayuda con tu proyecto digital. Nuestro equipo puede ayudarte a crear una solución personalizada. ¿Te gustaría que te contactemos por WhatsApp para darte más detalles?',
                                    audio_url: null // In production, this would be a URL
                                })
                            });
                        } else {
                            // For other webhooks, just return success
                            resolve({
                                ok: true,
                                json: () => Promise.resolve({ success: true })
                            });
                        }
                    }, 1500); // Simulate network delay
                } else {
                    // For non-local environments, use the original fetch
                    return originalFetch(url, options).then(resolve, reject);
                }
            } else {
                // For non-webhook calls, use the original fetch
                return originalFetch(url, options).then(resolve, reject);
            }
        });
    };
})(window.fetch);
