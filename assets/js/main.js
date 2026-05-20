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
        // Tema Claro/Oscuro
        darkMode: true,
        
        // Titulos dinámicos para DTR
        heroTitle: 'Multiplicá tus ventas y automatizá tu negocio con IA',
        heroSubtitle: 'Creamos chatbots de WhatsApp inteligentes, agentes de voz y automatizaciones a medida conectando tus herramientas favoritas.',
        
        // AI state
        aiMood: '',
        aiGreeting: '',
        
        // User mood state
        userMood: '',
        userMoodEmoji: '',
        userMoodResponse: '',
        selectedQuestion: '',
        selectedService: '',
        randomGreeting: '',
        
        // Saludos aleatorios por estado de ánimo
        moodGreetings: {
            'Alegre': [
                '¡Qué bueno verte con tanta energía positiva! 😄 ¿Qué te trae por acá hoy?',
                '¡Tu alegría es contagiosa! 🌟 ¿Qué proyecto digital te gustaría implementar?',
                'Con esa actitud positiva seguro lograrás grandes cosas 😊 ¿Qué te gustaría crear?',
                '¡Qué buena onda tenes hoy! 😀 ¿En qué podemos ayudarte a brillar aún más?'
            ],
            'Creativo': [
                'Las mejores ideas nacen de mentes creativas como la tuya 💡 ¿Qué estás pensando implementar?',
                '¡La creatividad es el primer paso hacia la innovación! 🎨 ¿Qué proyecto tenés en mente?',
                'Esa chispa creativa es justo lo que necesitamos ✨ ¿Qué te gustaría desarrollar hoy?',
                'Las mentes creativas transforman el mundo digital 🌍 ¿Qué solución estás buscando?'
            ],
            'Energético': [
                '¡Con esa energía podemos mover montañas digitales! ⚡ ¿Qué te gustaría acelerar hoy?',
                'Tu energía es el combustible perfecto para tu transformación digital 🚀 ¿Qué querés implementar?',
                '¡A toda máquina! 💪 ¿Qué proceso te gustaría optimizar con esa energía?',
                'La energía que traes es perfecta para proyectos ambiciosos 🎯 ¿Qué te gustaría lograr?'
            ],
            'Curioso': [
                'La curiosidad es el motor de la innovación 🤓 ¿Qué te gustaría descubrir hoy?',
                '¿Buscando nuevas posibilidades digitales? 🔍 ¿Qué te intriga más del mundo tech?',
                'Las mentes curiosas encuentran soluciones brillantes 💡 ¿Qué te gustaría explorar?',
                'Tu curiosidad te llevará lejos en el mundo digital 🌎 ¿Qué querés conocer hoy?'
            ],
            'Motivado': [
                '¡Con esa motivación, todo es posible en el mundo digital! 💪 ¿Qué objetivo tenés?',
                'La motivación es el primer paso hacia el éxito 🏁 ¿Qué te gustaría implementar?',
                'Esa actitud ganadora te llevará lejos 💼 ¿Qué proyecto digital te motiva hoy?',
                '¡Vamos con todo! 🙌 ¿Qué solución digital estás buscando implementar?'
            ]
        },
        
        // Opciones de servicios
        serviceOptions: [
            { id: 'automatizaciones', emoji: '🤖', text: 'Automatizaciones' },
            { id: 'ia-atencion', emoji: '💬', text: 'Atención al cliente con IA' },
            { id: 'web', emoji: '🌐', text: 'Quiero mi página web' },
            { id: 'sistemas', emoji: '💻', text: 'Sistemas personalizados' },
            { id: 'whatsapp', emoji: '📱', text: 'Chatbot de WhatsApp' },
            { id: 'ayuda', emoji: '🤔', text: 'No lo sé bien, ayudame' }
        ],
        
        // Respuestas personalizadas según estado de ánimo y servicio seleccionado
        moodServiceResponses: {
            'Alegre': {
                'automatizaciones': '¡Genial! Con tu energía positiva, vamos a crear automatizaciones que harán tu día a día mucho más fácil y divertido 😄',
                'ia-atencion': 'Tu buen humor es contagioso. Vamos a crear un asistente de IA que refleje esa misma alegría para tus clientes 😊',
                'web': '¡Excelente elección! Vamos a crear una página web tan vibrante y positiva como tú 🎉',
                'sistemas': 'Con esa actitud positiva, desarrollar un sistema personalizado será un proceso divertido y gratificante 😄',
                'whatsapp': '¡Fantástico! Vamos a crear un chatbot de WhatsApp tan alegre y dinámico como tú, que hará sonreír a tus clientes 😀',
                'ayuda': 'Me encanta tu entusiasmo. Vamos a explorar juntos todas las posibilidades para encontrar la solución perfecta para ti 🙌'
            },
            'Creativo': {
                'automatizaciones': 'Tu mente creativa es perfecta para diseñar flujos de automatización innovadores. Vamos a crear algo único 💡',
                'ia-atencion': 'Combinando tu creatividad con la IA, podemos diseñar experiencias de atención al cliente verdaderamente innovadoras 🎨',
                'web': 'Tu visión creativa + nuestro expertise técnico = una página web que destacará del resto ✨',
                'sistemas': 'Los sistemas más innovadores nacen de mentes creativas como la tuya. Vamos a diseñar algo revolucionario 💻',
                'whatsapp': 'Tu creatividad será la clave para diseñar un chatbot de WhatsApp único que sorprenderá a tus clientes con respuestas originales 🎨',
                'ayuda': 'Las mentes creativas como la tuya siempre encuentran soluciones innovadoras. Exploremos juntos las posibilidades 🧐'
            },
            'Energético': {
                'automatizaciones': 'Con esa energía, vamos a implementar automatizaciones que potencien tu productividad al máximo ⚡',
                'ia-atencion': 'Canalizaremos tu energía en un sistema de atención con IA que nunca duerme y siempre está listo para ayudar 💪',
                'web': '¡A toda máquina! Vamos a crear una página web dinámica y potente que refleje tu energía 🚀',
                'sistemas': 'Tu impulso es exactamente lo que se necesita para implementar sistemas robustos y eficientes. ¡Manos a la obra! 🛠️',
                'whatsapp': '¡Con esa energía, tu chatbot de WhatsApp estará listo para responder a tus clientes 24/7 sin perder el ritmo! ⚡📱',
                'ayuda': 'Con esa energía, encontraremos rápidamente la solución perfecta para tus necesidades. ¡Vamos a ello! 🏃‍♂️'
            },
            'Curioso': {
                'automatizaciones': 'Tu curiosidad nos llevará a descubrir formas innovadoras de automatizar procesos que ni siquiera habías imaginado 🧐',
                'ia-atencion': 'Las mentes curiosas como la tuya sacan el máximo provecho de la IA. Exploremos juntos cómo revolucionar tu atención al cliente 🔍',
                'web': 'Tu curiosidad nos ayudará a explorar nuevas tendencias y tecnologías para crear una web verdaderamente innovadora 🌌',
                'sistemas': 'Las preguntas que haces desde tu curiosidad nos ayudarán a diseñar un sistema que realmente se adapte a tus necesidades 🤓',
                'whatsapp': 'Tu curiosidad nos llevará a explorar todas las posibilidades de WhatsApp Business API para crear un chatbot inteligente y adaptable 🤔📱',
                'ayuda': 'La curiosidad es el primer paso hacia el conocimiento. Juntos descubriremos exactamente lo que necesitas 📖'
            },
            'Motivado': {
                'automatizaciones': 'Con tu motivación, implementaremos automatizaciones que te ayudarán a alcanzar tus objetivos más rápido 🏁',
                'ia-atencion': 'Tu motivación es clave para implementar con éxito un sistema de atención con IA que transforme tu negocio 📈',
                'web': 'Canalizaremos tu motivación en una página web que no solo se vea bien, sino que te ayude a alcanzar tus metas de negocio 💯',
                'sistemas': 'Con esa actitud, desarrollaremos un sistema que no solo cumpla con tus expectativas, sino que las supere 💪',
                'whatsapp': 'Tu motivación nos impulsará a crear un chatbot de WhatsApp que transforme la manera en que te comunicas con tus clientes 💪📱',
                'ayuda': 'Tu motivación es inspiradora. Juntos encontraremos la solución perfecta para impulsar tu éxito 🚀'
            }
        },
        
        // Voice recording state
        isRecording: false,
        mediaRecorder: null,
        audioChunks: [],
        typedInquiry: '',
        voiceResponse: '',
        audioResponse: null,
        
        // Conversational Chatbot Funnel state
        chatStep: 'inquiry', // inquiry, name, province, phone, calendar, finished
        chatInquiry: '',
        chatName: '',
        chatProvince: '',
        chatPhone: '',
        chatResponseText: '',
        chatDate: '',
        chatTime: '',
        availableTimes: ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00'],
        availableDates: [],
        industryTab: 'inmo',
        chatbotThinking: false,
        
        // Form state
        form: {
            nombre: '',
            telefono: '',
            email: '',
            message: '',
            estado_animo: ''
        },
        formSubmitted: false,
        formSuccess: false,
        formSuccessMessage: '',
        
        // Browser info for analytics
        browserInfo: {
            name: 'Chrome',
            time: new Date().toLocaleTimeString()
        },
        
        // Initialize the app
        init() {
            try {
                console.log('Inicializando la aplicación...');
                this.initTheme();
                this.initDynamicPersonalization();
                
                // Verificar que CONFIG esté cargado
                if (typeof CONFIG === 'undefined') {
                    console.error('Error: El objeto CONFIG no está definido. Asegúrate de que config.js se cargue antes que main.js');
                    return;
                }
                
                // Configurar información del navegador
                this.browserInfo.name = this.getBrowserName();
                this.browserInfo.time = new Date().toLocaleTimeString();
                
                // Inicializar animaciones
                this.initScrollAnimations();
                this.setupScrollIndicator();
                this.initScrollspy();
                
                // Establecer directamente un estado de ánimo y saludo aleatorios
                this.setRandomMoodAndGreeting();
                
                // Inicializar el mensaje del chatbot si hay elementos guardados
                this.initChatbotMessage();
                
                // Generar fechas hábiles disponibles (los próximos 5 días de Lunes a Viernes)
                const datesList = [];
                let dateCursor = new Date();
                dateCursor.setDate(dateCursor.getDate() + 1); // Empezar desde mañana
                while (datesList.length < 5) {
                    const dayOfWeek = dateCursor.getDay();
                    if (dayOfWeek !== 0 && dayOfWeek !== 6) { // Evitar Sábado (0 = Domingo, 6 = Sábado)
                        const dateFormatted = dateCursor.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
                        const cap = dateFormatted.charAt(0).toUpperCase() + dateFormatted.slice(1);
                        datesList.push({
                            value: dateCursor.toISOString().split('T')[0],
                            label: cap
                        });
                    }
                    dateCursor.setDate(dateCursor.getDate() + 1);
                }
                this.availableDates = datesList;
                
                console.log('Aplicación inicializada correctamente');
            } catch (error) {
                console.error('Error durante la inicialización:', error);
            }
        },
        
        // Inicializar el mensaje del chatbot
        initChatbotMessage() {
            try {
                // Elementos del chatbot
                const selectedServiceText = document.getElementById('selectedServiceText');
                const chatMoodBadge = document.getElementById('chatMoodBadge');
                const chatServiceEmoji = document.getElementById('chatServiceEmoji');
                const chatServiceText = document.getElementById('chatServiceText');
                
                // Verificar si hay un servicio guardado en localStorage
                const savedServiceJSON = localStorage.getItem('selectedService');
                const savedMood = localStorage.getItem('currentMood');
                
                if (savedServiceJSON && selectedServiceText && chatServiceText && chatServiceEmoji) {
                    try {
                        const savedService = JSON.parse(savedServiceJSON);
                        
                        if (savedService && savedService.text) {
                            // Actualizar el texto del servicio en el mensaje
                            selectedServiceText.textContent = savedService.text;
                            chatServiceText.textContent = savedService.text;
                            
                            // Actualizar el emoji si está disponible
                            if (savedService.emoji) {
                                chatServiceEmoji.textContent = savedService.emoji;
                            }
                            
                            console.log('Mensaje del chatbot inicializado con servicio guardado:', savedService.text);
                        }
                    } catch (e) {
                        console.error('Error al parsear el servicio guardado:', e);
                    }
                }
                
                // Actualizar el estado de ánimo si está guardado
                if (savedMood && chatMoodBadge) {
                    chatMoodBadge.textContent = 'Estado de ánimo: ' + savedMood;
                    console.log('Estado de ánimo del chatbot actualizado:', savedMood);
                }
            } catch (error) {
                console.error('Error al inicializar el mensaje del chatbot:', error);
            }
        },
        
        // Establecer directamente un estado de ánimo y saludo aleatorios
        setRandomMoodAndGreeting() {
            try {
                console.log('Estableciendo estado de ánimo y saludo aleatorios...');
                
                // Lista de estados de ánimo disponibles
                const availableMoods = [
                    { mood: 'Alegre', emoji: '😄' },
                    { mood: 'Creativo', emoji: '🎨' },
                    { mood: 'Energético', emoji: '⚡' },
                    { mood: 'Curioso', emoji: '🤔' },
                    { mood: 'Motivado', emoji: '💪' }
                ];
                
                // Seleccionar un estado de ánimo aleatorio
                const randomMoodIndex = Math.floor(Math.random() * availableMoods.length);
                const selectedMood = availableMoods[randomMoodIndex];
                
                // Establecer el estado de ánimo seleccionado
                this.userMood = selectedMood.mood;
                this.userMoodEmoji = selectedMood.emoji;
                
                // Actualizar el badge de estado de ánimo en el DOM
                const moodBadgeElement = document.getElementById('moodBadge');
                if (moodBadgeElement) {
                    moodBadgeElement.textContent = 'Estado de ánimo: ' + this.userMood;
                }
                
                // Seleccionar un saludo aleatorio para este estado de ánimo
                if (this.moodGreetings[this.userMood] && this.moodGreetings[this.userMood].length > 0) {
                    const randomGreetingIndex = Math.floor(Math.random() * this.moodGreetings[this.userMood].length);
                    this.randomGreeting = this.moodGreetings[this.userMood][randomGreetingIndex];
                    
                    // Actualizar el saludo en el DOM
                    const greetingElement = document.getElementById('personalizedGreeting');
                    if (greetingElement) {
                        greetingElement.textContent = this.randomGreeting;
                        console.log('Saludo aleatorio establecido en el DOM:', this.randomGreeting);
                    } else {
                        console.error('No se encontró el elemento personalizedGreeting en el DOM');
                    }
                } else {
                    console.error('No hay saludos disponibles para el estado de ánimo:', this.userMood);
                }
                
                console.log('Estado de ánimo y saludo aleatorios establecidos correctamente');
            } catch (error) {
                console.error('Error al establecer estado de ánimo y saludo aleatorios:', error);
            }
        },
        
        // Seleccionar un estado de ánimo aleatorio
        selectRandomMood() {
            try {
                console.log('Seleccionando estado de ánimo aleatorio...');
                
                // Lista de estados de ánimo disponibles
                const availableMoods = [
                    { mood: 'Alegre', emoji: '😄' },
                    { mood: 'Creativo', emoji: '🎨' },
                    { mood: 'Energético', emoji: '⚡' },
                    { mood: 'Curioso', emoji: '🤔' },
                    { mood: 'Motivado', emoji: '💪' }
                ];
                
                // Seleccionar un estado de ánimo aleatorio
                const randomIndex = Math.floor(Math.random() * availableMoods.length);
                const selectedMood = availableMoods[randomIndex];
                
                console.log('Estado de ánimo aleatorio seleccionado:', selectedMood.mood);
                
                // Establecer el estado de ánimo seleccionado
                this.setUserMood(selectedMood.mood, selectedMood.emoji);
                
            } catch (error) {
                console.error('Error al seleccionar estado de ánimo aleatorio:', error);
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
                
                // Seleccionar un saludo aleatorio para este estado de ánimo
                if (this.moodGreetings[mood] && this.moodGreetings[mood].length > 0) {
                    const randomIndex = Math.floor(Math.random() * this.moodGreetings[mood].length);
                    this.randomGreeting = this.moodGreetings[mood][randomIndex];
                    console.log('Saludo aleatorio seleccionado:', this.randomGreeting);
                    
                    // Actualizar directamente el elemento del DOM con el saludo
                    const greetingElement = document.getElementById('personalizedGreeting');
                    if (greetingElement) {
                        greetingElement.textContent = this.randomGreeting;
                        console.log('Saludo establecido directamente en el DOM');
                    } else {
                        console.error('No se encontró el elemento personalizedGreeting en el DOM');
                    }
                } else {
                    this.randomGreeting = `¡Hola! ¿Qué te trae por aquí hoy?`;
                    // Actualizar con el saludo predeterminado
                    const greetingElement = document.getElementById('personalizedGreeting');
                    if (greetingElement) {
                        greetingElement.textContent = this.randomGreeting;
                    }
                }
                
                // Establecer respuesta inicial desde CONFIG si está disponible
                if (CONFIG.userMoodResponses && CONFIG.userMoodResponses[mood]) {
                    this.userMoodResponse = CONFIG.userMoodResponses[mood];
                } else {
                    this.userMoodResponse = `Has seleccionado que te sientes ${mood}. ¡Genial!`;
                }
                
                // Guardar el estado de ánimo en el formulario
                this.form.estado_animo = mood;
                
                // Enviar el estado de ánimo al webhook
                this.sendMoodWebhook(mood);
                
                // Resetear la pregunta y servicio seleccionados
                this.selectedQuestion = '';
                this.selectedService = '';
                
                console.log('Estado de ánimo del usuario establecido:', this.userMood);
                console.log('Saludo aleatorio seleccionado:', this.randomGreeting);
            } catch (error) {
                console.error('Error al establecer el estado de ánimo del usuario:', error);
            }
        },
        
        // Handle service selection
        selectService(serviceId) {
            try {
                console.log('Servicio seleccionado:', serviceId);
                
                // Buscar el servicio en la lista de servicios disponibles
                const selectedService = this.serviceOptions.find(service => service.id === serviceId) || {
                    id: serviceId,
                    emoji: '❓',
                    text: serviceId
                };
                
                // Establecer el servicio seleccionado
                this.selectedService = serviceId;
                
                // Guardar en localStorage para persistencia y chatbot
                localStorage.setItem('selectedService', JSON.stringify(selectedService));
                
                // Actualizar dinámicamente los textos del chatbot en tiempo real
                const domSelectedServiceText = document.getElementById('selectedServiceText');
                const domChatServiceText = document.getElementById('chatServiceText');
                const domChatServiceEmoji = document.getElementById('chatServiceEmoji');
                
                if (domSelectedServiceText) domSelectedServiceText.textContent = selectedService.text;
                if (domChatServiceText) domChatServiceText.textContent = selectedService.text;
                if (domChatServiceEmoji) domChatServiceEmoji.textContent = selectedService.emoji;
                
                // Obtener respuesta personalizada basada en el estado de ánimo y el servicio
                if (this.moodServiceResponses[this.userMood] && this.moodServiceResponses[this.userMood][serviceId]) {
                    this.selectedQuestion = this.moodServiceResponses[this.userMood][serviceId];
                } else {
                    this.selectedQuestion = `Has seleccionado ${selectedService.text}. ¡Excelente elección! Contanos más sobre tu idea.`;
                }
                
                // Guardar datos en la base de datos
                this.saveUserSelectionToDatabase();
                
                // Enviar el servicio seleccionado al webhook
                this.sendServiceWebhook(this.userMood, serviceId, selectedService.text);
                
                console.log('Servicio seleccionado:', this.selectedService);
                console.log('Respuesta personalizada:', this.selectedQuestion);
            } catch (error) {
                console.error('Error al seleccionar servicio:', error);
            }
        },
        
        // Función combinada para seleccionar servicio y desplazarse a la sección de voz
        selectServiceAndScroll(serviceId) {
            try {
                console.log('Seleccionando servicio y desplazándose a la sección de voz:', serviceId);
                
                // Primero seleccionar el servicio
                this.selectService(serviceId);
                
                // Luego desplazarse a la sección de voz
                const voiceSection = document.getElementById('voice-section');
                if (voiceSection) {
                    setTimeout(() => {
                        voiceSection.scrollIntoView({ behavior: 'smooth' });
                        console.log('Desplazamiento a la sección de voz completado');
                    }, 500);
                } else {
                    console.error('No se encontró la sección de voz');
                }
            } catch (error) {
                console.error('Error al seleccionar servicio y desplazarse:', error);
            }
        },
        
        // Scroll to voice section
        scrollToVoiceSection() {
            try {
                console.log('Desplazándose a la sección de voz...');
                const voiceSection = document.getElementById('voice-section');
                if (voiceSection) {
                    setTimeout(() => {
                        voiceSection.scrollIntoView({ behavior: 'smooth' });
                    }, 500); // Pequeño retraso para que se complete la animación de la respuesta
                }
            } catch (error) {
                console.error('Error al desplazarse a la sección de voz:', error);
            }
        },
        
        // Guardar selección del usuario en la base de datos
        saveUserSelectionToDatabase() {
            try {
                console.log('Guardando datos del usuario en la base de datos...');
                
                // Crear objeto con los datos del usuario
                const userData = {
                    timestamp: new Date().toISOString(),
                    userMood: this.userMood,
                    userMoodEmoji: this.userMoodEmoji,
                    selectedService: this.selectedService,
                    browserInfo: this.browserInfo,
                    randomGreeting: this.randomGreeting
                };
                
                console.log('Datos a guardar:', userData);
                
                // Enviar datos a un endpoint de backend para guardarlos
                if (typeof CONFIG !== 'undefined' && CONFIG.database && CONFIG.database.url) {
                    fetch(CONFIG.database.url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(userData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Datos guardados correctamente:', data);
                    })
                    .catch(error => {
                        console.error('Error al guardar datos:', error);
                    });
                } else {
                    // Si no hay configuración de base de datos, guardar en localStorage como respaldo
                    const storedSelections = JSON.parse(localStorage.getItem('userSelections') || '[]');
                    storedSelections.push(userData);
                    localStorage.setItem('userSelections', JSON.stringify(storedSelections));
                    console.log('Datos guardados en localStorage como respaldo');
                }
                
            } catch (error) {
                console.error('Error al guardar datos del usuario:', error);
            }
        },
        
        // Send service to webhook
        sendServiceWebhook(mood, serviceId, serviceText) {
            try {
                console.log('Enviando servicio seleccionado al webhook...');
                
                // Prepare data for webhook
                const webhookData = {
                    estado_animo: mood,
                    servicio_id: serviceId,
                    servicio_texto: serviceText,
                    navegador: this.browserInfo.name,
                    hora: this.browserInfo.time
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando envío de servicio:', webhookData);
                } else {
                    // In production, make an actual API call
                    fetch(CONFIG.webhooks.mood, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook de servicio:', data);
                    })
                    .catch(error => {
                        console.error('Error al enviar servicio al webhook:', error);
                    });
                }
            } catch (error) {
                console.error('Error al enviar el servicio al webhook:', error);
            }
        },
        
        // Send selected question to webhook
        sendQuestionWebhook(mood, question) {
            try {
                console.log('Enviando pregunta seleccionada al webhook...');
                
                // Prepare data for webhook
                const webhookData = {
                    estado_animo: mood,
                    pregunta: question,
                    navegador: this.browserInfo.name,
                    hora: this.browserInfo.time
                };
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                          window.location.hostname === '127.0.0.1' ||
                                          window.location.hostname.includes('.test') ||
                                          window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando envío de pregunta:', webhookData);
                } else {
                    // In production, make an actual API call
                    fetch(CONFIG.webhooks.mood, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook de pregunta:', data);
                    })
                    .catch(error => {
                        console.error('Error al enviar pregunta al webhook:', error);
                    });
                }
            } catch (error) {
                console.error('Error al enviar la pregunta al webhook:', error);
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
        
        // Request microphone permission and then toggle recording
        requestMicrophonePermission() {
            try {
                console.log('Solicitando permisos de micrófono...');
                
                // Check if we already have permission
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        // Stop the stream immediately as we're just checking permissions
                        stream.getTracks().forEach(track => track.stop());
                        
                        console.log('Permisos de micrófono concedidos');
                        // Now that we have permission, toggle recording
                        this.toggleRecording();
                    })
                    .catch(error => {
                        console.error('Error al solicitar permisos de micrófono:', error);
                        alert('Para grabar un mensaje de voz, necesitamos acceso a tu micrófono. Por favor, concede los permisos cuando el navegador te lo solicite.');
                    });
            } catch (error) {
                console.error('Error al solicitar permisos de micrófono:', error);
                alert('Tu navegador no soporta la grabación de audio o hubo un error al solicitar los permisos.');
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
                
                // Reset state
                this.isRecording = true;
                this.audioChunks = [];
                this.voiceResponse = ''; // Clear any previous response
                
                // Update button text and style
                const recordButton = document.getElementById('recordButton');
                if (recordButton) {
                    recordButton.classList.add('animate-pulse');
                    const buttonText = recordButton.querySelector('span');
                    if (buttonText) {
                        buttonText.textContent = 'Detener grabación';
                    }
                    
                    // Change icon to stop icon
                    const iconContainer = recordButton.querySelector('.mic-icon-container');
                    if (iconContainer) {
                        iconContainer.innerHTML = `
                            <svg class="w-8 h-8" fill="white" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"></path>
                            </svg>
                        `;
                    }
                }
                
                // Check if browser supports MediaRecorder
                if (!window.MediaRecorder) {
                    throw new Error('Tu navegador no soporta la grabación de audio. Por favor, intenta con Chrome, Firefox o Edge.');
                }
                
                // Request microphone access
                navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    } 
                })
                .then(stream => {
                    try {
                        // Create MediaRecorder instance
                        this.mediaRecorder = new MediaRecorder(stream);
                        
                        // Set up event listeners
                        this.mediaRecorder.addEventListener('dataavailable', event => {
                            if (event.data.size > 0) {
                                this.audioChunks.push(event.data);
                                console.log('Fragmento de audio capturado:', event.data.size, 'bytes');
                            }
                        });
                        
                        this.mediaRecorder.addEventListener('stop', () => {
                            try {
                                console.log('Grabación detenida, procesando audio...');
                                console.log('Fragmentos de audio capturados:', this.audioChunks.length);
                                
                                if (this.audioChunks.length === 0) {
                                    console.error('No se capturaron datos de audio');
                                    alert('No se capturó ningún audio. Por favor, intenta nuevamente.');
                                    return;
                                }
                                
                                // Create audio blob
                                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                                console.log('Tamaño del blob de audio:', audioBlob.size, 'bytes');
                                
                                if (audioBlob.size === 0) {
                                    console.error('El blob de audio está vacío');
                                    alert('No se capturó ningún audio. Por favor, intenta nuevamente.');
                                    return;
                                }
                                
                                // Create a URL for the blob (for debugging/preview)
                                const audioUrl = URL.createObjectURL(audioBlob);
                                console.log('URL del audio creada:', audioUrl);
                                
                                // Convert to base64
                                const reader = new FileReader();
                                reader.readAsDataURL(audioBlob);
                                reader.onloadend = () => {
                                    try {
                                        const base64data = reader.result.split(',')[1];
                                        console.log('Audio convertido a base64 correctamente');
                                        
                                        // Send to webhook
                                        this.sendAudioWebhook(base64data);
                                    } catch (error) {
                                        console.error('Error al procesar el audio en base64:', error);
                                        alert('Error al procesar el audio. Por favor, intenta nuevamente.');
                                    }
                                };
                                
                                reader.onerror = (error) => {
                                    console.error('Error al leer el blob de audio:', error);
                                    alert('Error al procesar el audio. Por favor, intenta nuevamente.');
                                };
                            } catch (error) {
                                console.error('Error al procesar la grabación de audio:', error);
                                alert('Error al procesar el audio. Por favor, intenta nuevamente.');
                            }
                        });
                        
                        // Start recording
                        this.mediaRecorder.start(1000); // Collect data in 1-second chunks
                        console.log('Grabación iniciada correctamente con MediaRecorder:', this.mediaRecorder.state);
                    } catch (error) {
                        console.error('Error al configurar el MediaRecorder:', error);
                        alert('Error al iniciar la grabación. Por favor, intenta nuevamente.');
                        this.isRecording = false;
                        
                        // Reset button
                        this.resetRecordButton();
                        
                        // Stop all tracks in the stream
                        if (stream) {
                            stream.getTracks().forEach(track => track.stop());
                        }
                    }
                })
                .catch(error => {
                    console.error('Error al acceder al micrófono:', error);
                    
                    let errorMessage = 'No se pudo acceder al micrófono. ';
                    
                    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                        errorMessage += 'Has denegado el permiso para usar el micrófono. Por favor, actualiza los permisos en la configuración de tu navegador.';
                    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                        errorMessage += 'No se detectó ningún micrófono. Por favor, conecta un micrófono e intenta nuevamente.';
                    } else {
                        errorMessage += 'Por favor, verifica los permisos del navegador e intenta nuevamente.';
                    }
                    
                    alert(errorMessage);
                    this.isRecording = false;
                    this.resetRecordButton();
                });
            } catch (error) {
                console.error('Error al iniciar la grabación:', error);
                alert('Error al iniciar la grabación: ' + error.message);
                this.isRecording = false;
                this.resetRecordButton();
            }
        },
        
        // Reset record button to initial state
        resetRecordButton() {
            try {
                const recordButton = document.getElementById('recordButton');
                if (recordButton) {
                    // Remove animation
                    recordButton.classList.remove('animate-pulse');
                    
                    // Reset text
                    const buttonText = recordButton.querySelector('span');
                    if (buttonText) {
                        buttonText.textContent = 'Grabar mensaje';
                    }
                    
                    // Reset icon to microphone
                    const iconContainer = recordButton.querySelector('.mic-icon-container');
                    if (iconContainer) {
                        iconContainer.innerHTML = `
                            <svg class="w-8 h-8" fill="white" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"></path>
                                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"></path>
                            </svg>
                        `;
                    }
                }
            } catch (error) {
                console.error('Error al resetear el botón de grabación:', error);
            }
        },
        
        // Stop voice recording
        stopRecording() {
            try {
                console.log('Deteniendo grabación de voz...');
                
                if (this.mediaRecorder && this.isRecording) {
                    // Check if mediaRecorder is in recording state
                    if (this.mediaRecorder.state === 'recording') {
                        console.log('MediaRecorder está grabando, deteniendo...');
                        this.mediaRecorder.stop();
                    } else {
                        console.log('MediaRecorder no está grabando, estado actual:', this.mediaRecorder.state);
                    }
                    
                    this.isRecording = false;
                    
                    // Reset button to initial state
                    this.resetRecordButton();
                    
                    // Stop all audio tracks
                    if (this.mediaRecorder.stream) {
                        console.log('Deteniendo todas las pistas de audio...');
                        this.mediaRecorder.stream.getTracks().forEach(track => {
                            track.stop();
                            console.log('Pista de audio detenida:', track.kind);
                        });
                    }
                    
                    console.log('Grabación detenida correctamente');
                } else {
                    console.warn('No hay grabación activa para detener');
                    this.isRecording = false;
                    this.resetRecordButton();
                }
            } catch (error) {
                console.error('Error al detener la grabación:', error);
                alert('Hubo un error al detener la grabación. Por favor, recarga la página e intenta nuevamente.');
                this.isRecording = false;
                this.resetRecordButton();
            }
        },
        
        getSelectedService() {
            try {
                return JSON.parse(localStorage.getItem('selectedService') || '{}');
            } catch (error) {
                return {};
            }
        },

        showChatbotResponse(message, audioUrl = null) {
            const initialMessage = document.getElementById('initialChatbotMessage');
            const voiceResponseContainer = document.getElementById('voiceResponseContainer');
            const voiceResponseText = document.getElementById('voiceResponseText');
            const audioResponseContainer = document.getElementById('audioResponseContainer');
            const audioResponsePlayer = document.getElementById('audioResponsePlayer');

            if (initialMessage) {
                initialMessage.style.display = 'none';
            }

            if (voiceResponseContainer) {
                voiceResponseContainer.style.display = 'block';
            }

            if (voiceResponseText) {
                voiceResponseText.textContent = message;
            }

            if (audioUrl && audioResponseContainer && audioResponsePlayer) {
                audioResponsePlayer.src = audioUrl;
                audioResponseContainer.style.display = 'block';
            }
        },

        buildChatbotPayload(extraData = {}) {
            const selectedService = this.getSelectedService();

            return {
                session_id: localStorage.getItem('nlp_session_id') || this.createSessionId(),
                source: 'landing',
                nombre: this.form.nombre || '',
                telefono: this.form.telefono || '',
                email: this.form.email || '',
                selectedService,
                estado_animo: this.userMood || localStorage.getItem('currentMood') || '',
                navegador: this.getBrowserName(),
                created_at: new Date().toISOString(),
                ...extraData
            };
        },

        createSessionId() {
            const sessionId = 'nlp_' + Date.now() + '_' + Math.random().toString(16).slice(2);
            localStorage.setItem('nlp_session_id', sessionId);
            return sessionId;
        },

        sendTextWebhook() {
            const message = (this.typedInquiry || '').trim();

            if (!message) {
                alert('Escribí una consulta para que la IA pueda responder.');
                return;
            }

            this.chatInquiry = message;
            this.chatbotThinking = true;
            
            // Ocultar el mensaje inicial y mostrar contenedor de respuestas si existen
            const initialMessage = document.getElementById('initialChatbotMessage');
            const voiceResponseContainer = document.getElementById('voiceResponseContainer');
            const voiceResponseText = document.getElementById('voiceResponseText');
            if (initialMessage && voiceResponseContainer) {
                initialMessage.style.display = 'none';
                voiceResponseContainer.style.display = 'block';
            }
            if (voiceResponseText) {
                voiceResponseText.textContent = 'Procesando tu consulta con la IA...';
            }

            // Generar tip genérico y simple basado en palabras clave
            let tip = '';
            const msgLower = message.toLowerCase();
            if (msgLower.includes('whatsapp') || msgLower.includes('chat') || msgLower.includes('atencion') || msgLower.includes('atención')) {
                tip = '¡Excelente iniciativa! Diseñar agentes de WhatsApp autónomos integrados con n8n te va a permitir responder de forma instantánea a tus clientes las 24 horas, eliminando la pérdida de leads por demoras de respuesta.';
            } else if (msgLower.includes('automatiz') || msgLower.includes('operac') || msgLower.includes('flujo') || msgLower.includes('sheets') || msgLower.includes('crm')) {
                tip = '¡Las automatizaciones operativas son la clave! Conectar tus sistemas (WhatsApp, CRM y planillas) te permitirá eliminar la carga manual de datos, evitar errores humanos y ahorrar más de 15 horas de trabajo semanales.';
            } else if (msgLower.includes('web') || msgLower.includes('landing') || msgLower.includes('pagin') || msgLower.includes('página') || msgLower.includes('diseño')) {
                tip = '¡Estructurar una landing page es vital! Diseñar una web rápida y optimizada para conversión te dará la imagen premium y profesional necesaria para atraer leads realmente interesados en contratarte.';
            } else {
                tip = '¡Qué gran proyecto! Implementar una solución digital con inteligencia artificial y automatización te permitirá estandarizar la atención al cliente, optimizar tareas repetitivas y escalar tu negocio.';
            }

            const webhookData = this.buildChatbotPayload({
                message,
                wants_voice_response: false
            });

            // Detectar si es entorno local
            const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                       window.location.hostname === '127.0.0.1' ||
                                       window.location.hostname.includes('.test') ||
                                       window.location.hostname.includes('.local');

            if (isLocalEnvironment) {
                console.log('Simulando chatbot local con tip...');
                setTimeout(() => {
                    this.chatResponseText = tip;
                    this.chatStep = 'name';
                    this.chatbotThinking = false;
                    this.showChatbotResponse(tip);
                }, 1500);
            } else {
                fetch(CONFIG.webhooks.chatbot, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(webhookData)
                })
                .then(response => response.json())
                .then(data => {
                    const aiReply = data.reply || data.text_response || '';
                    this.chatResponseText = tip + (aiReply ? ' \n\nAdemás, la IA propone: ' + aiReply : '');
                    this.chatStep = 'name';
                    this.chatbotThinking = false;
                    this.showChatbotResponse(this.chatResponseText, data.audio_url || null);
                })
                .catch(error => {
                    console.error('Error al enviar consulta al chatbot:', error);
                    this.chatResponseText = tip + ' (Nota: no pudimos conectar con el servidor principal, pero podemos agendar para armar tu plan).';
                    this.chatStep = 'name';
                    this.chatbotThinking = false;
                    this.showChatbotResponse(this.chatResponseText);
                });
            }
        },

        // Send recorded audio to webhook
        sendAudioWebhook(audioBase64) {
            try {
                console.log('Enviando audio al webhook...');
                
                // Ocultar el mensaje inicial del chatbot
                const initialMessage = document.getElementById('initialChatbotMessage');
                const voiceResponseContainer = document.getElementById('voiceResponseContainer');
                const voiceResponseText = document.getElementById('voiceResponseText');
                
                if (initialMessage && voiceResponseContainer && voiceResponseText) {
                    initialMessage.style.display = 'none';
                    voiceResponseContainer.style.display = 'block';
                    voiceResponseText.textContent = 'Procesando tu mensaje de voz...';
                }
                
                this.chatbotThinking = true;
                
                // Obtener servicio seleccionado para el tip
                let selectedServiceText = 'tu proyecto';
                let selectedServiceId = '';
                try {
                    const selectedServiceObj = JSON.parse(localStorage.getItem('selectedService') || '{}');
                    if (selectedServiceObj && selectedServiceObj.text) {
                        selectedServiceText = selectedServiceObj.text;
                        selectedServiceId = selectedServiceObj.id;
                    }
                } catch (e) {
                    console.error('Error al parsear el servicio seleccionado:', e);
                }

                this.chatInquiry = `Mensaje de voz sobre ${selectedServiceText}`;

                // Generar tip basado en el servicio seleccionado
                let tip = '';
                if (selectedServiceId === 'automatizaciones' || selectedServiceId === 'sistemas') {
                    tip = '¡Excelente audio! Las automatizaciones e integraciones personalizadas con n8n son clave para eliminar las tareas mecánicas repetitivas. Automatizar este proceso te va a permitir ahorrar tiempo valioso y centrarte en expandir tu negocio.';
                } else if (selectedServiceId === 'ia-atencion' || selectedServiceId === 'whatsapp') {
                    tip = '¡Gran idea la que contás! Implementar un agente virtual inteligente en WhatsApp que responda de forma autónoma con RAG garantiza que ningún lead se pierda por demoras, aumentando tus ventas y manteniendo tu negocio abierto 24/7.';
                } else if (selectedServiceId === 'web') {
                    tip = '¡Buenísimo! Una landing page rápida, atractiva y optimizada con llamadas a la acción claras (CTA) es el núcleo de cualquier embudo de ventas exitoso para captar clientes en piloto automático.';
                } else {
                    tip = '¡Qué buen proyecto! Digitalizar y automatizar tus operaciones repetitivas con inteligencia artificial te va a liberar horas semanales de gestión manual y te dará una estructura escalable.';
                }

                const webhookData = this.buildChatbotPayload({
                    audio_base64: audioBase64,
                    audio_mime_type: 'audio/webm',
                    wants_voice_response: true,
                    message: this.typedInquiry || `Mensaje de voz sobre ${selectedServiceText}`
                });
                
                // Check if we're in a local environment
                const isLocalEnvironment = window.location.hostname === 'localhost' || 
                                           window.location.hostname === '127.0.0.1' ||
                                           window.location.hostname.includes('.test') ||
                                           window.location.hostname.includes('.local');
                
                if (isLocalEnvironment) {
                    console.log('Entorno local detectado. Simulando respuesta del webhook de audio...');
                    setTimeout(() => {
                        this.chatResponseText = tip;
                        this.chatStep = 'name';
                        this.chatbotThinking = false;
                        this.showChatbotResponse(tip);
                    }, 2000);
                } else {
                    fetch(CONFIG.webhooks.chatbot, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(webhookData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Respuesta del webhook de audio:', data);
                        const aiReply = data.reply || data.text_response || data.transcription || '';
                        this.chatResponseText = tip + (aiReply ? ' \n\nTranscripción/Propuesta: ' + aiReply : '');
                        this.chatStep = 'name';
                        this.chatbotThinking = false;
                        this.showChatbotResponse(this.chatResponseText, data.audio_url || null);
                    })
                    .catch(error => {
                        console.error('Error al enviar audio al webhook:', error);
                        this.chatResponseText = tip + ' (Nota: recibimos tu audio pero falló la conexión remota, continuamos para agendar).';
                        this.chatStep = 'name';
                        this.chatbotThinking = false;
                        this.showChatbotResponse(this.chatResponseText);
                    });
                }
            } catch (error) {
                console.error('Error al enviar el audio al webhook:', error);
                this.chatbotThinking = false;
                this.chatStep = 'name';
            }
        },

        // Submit accumulated lead conversational data to webhook
        submitChatbotLeadData() {
            const payload = this.buildChatbotPayload({
                nombre: this.chatName,
                provincia: this.chatProvince,
                telefono: this.chatPhone,
                inquiry: this.chatInquiry,
                fecha_reunion: this.chatDate,
                hora_reunion: this.chatTime,
                scheduled: !!(this.chatDate && this.chatTime),
                message: `Lead Conversacional: "${this.chatInquiry}". Cliente: ${this.chatName}. Provincia: ${this.chatProvince}. Teléfono: ${this.chatPhone}. Agenda llamada: ${this.chatDate || 'No agendada'} ${this.chatTime || ''}`
            });

            console.log('Enviando Lead conversacional al webhook:', payload);
            
            fetch(CONFIG.webhooks.newLead, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(res => {
                console.log('Lead enviado con éxito a n8n');
            })
            .catch(err => {
                console.error('Error al enviar Lead de chatbot a n8n:', err);
            });
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
                
                // Update button text and style
                const submitButton = document.getElementById('submitButton');
                if (submitButton) {
                    const buttonText = submitButton.querySelector('span');
                    if (buttonText) {
                        buttonText.textContent = 'Enviando...';
                    }
                    
                    // Add loading animation
                    submitButton.classList.add('opacity-75');
                    
                    // Change icon to loading spinner
                    const icon = submitButton.querySelector('svg');
                    if (icon) {
                        icon.outerHTML = `
                            <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" stroke="none" fill="currentColor"></path>
                            </svg>
                        `;
                    }
                }
                
                const webhookData = this.buildChatbotPayload({
                    nombre: this.form.nombre,
                    telefono: this.form.telefono,
                    email: this.form.email,
                    message: this.form.message || 'Quiero que me contacten para conversar un proyecto con IA y automatizacion.',
                    wants_voice_response: false
                });
                
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
                        this.formSuccessMessage = 'Demo local: la IA recibio tus datos y preparo el seguimiento.';
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
                        this.formSuccessMessage = data.reply || 'Te vamos a responder por WhatsApp o email con el resumen y el proximo paso.';
                    })
                    .catch(error => {
                        console.error('Error al enviar formulario:', error);
                        alert('Hubo un error al enviar el formulario. Por favor, intenta nuevamente.');
                        this.formSubmitted = false;
                        this.resetSubmitButton();
                    });
                }
            } catch (error) {
                console.error('Error al enviar el formulario:', error);
                alert('Hubo un error al enviar el formulario. Por favor, intenta nuevamente.');
                this.formSubmitted = false;
                this.resetSubmitButton();
            }
        },
        
        // Reset submit button to initial state
        resetSubmitButton() {
            try {
                const submitButton = document.getElementById('submitButton');
                if (submitButton) {
                    // Remove loading state
                    submitButton.classList.remove('opacity-75');
                    
                    // Reset text
                    const buttonText = submitButton.querySelector('span');
                    if (buttonText) {
                        buttonText.textContent = 'Conectar con la IA';
                    }
                    
                    // Reset icon to send icon
                    const icon = submitButton.querySelector('svg');
                    if (icon) {
                        icon.outerHTML = `
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
                            </svg>
                        `;
                    }
                }
            } catch (error) {
                console.error('Error al resetear el botón de envío:', error);
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
                
                // Smooth scroll and slide effect for links
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                    anchor.addEventListener('click', function (e) {
                        const targetId = this.getAttribute('href');
                        if (targetId === '#') return;
                        
                        const targetElement = document.querySelector(targetId);
                        if (targetElement) {
                            e.preventDefault();
                            targetElement.scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                            });
                            
                            // Apply slide transition effect
                            targetElement.classList.remove('slide-focus');
                            void targetElement.offsetWidth; // Trigger reflow
                            targetElement.classList.add('slide-focus');
                            setTimeout(() => {
                                targetElement.classList.remove('slide-focus');
                            }, 1000);
                        }
                    });
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
        
        // Initialize scrollspy for floating navbar
        initScrollspy() {
            try {
                console.log('Inicializando Scrollspy...');
                
                // Active targets
                const sections = [
                    document.getElementById('welcomeMessage'),
                    document.getElementById('solutions-section'),
                    document.getElementById('roi-section'),
                    document.getElementById('faq-section')
                ].filter(el => el !== null);
                
                const navLinks = document.querySelectorAll('.floating-nav a[href^="#"]');
                if (sections.length === 0 || navLinks.length === 0) return;

                const observerOptions = {
                    root: null,
                    rootMargin: '-30% 0px -50% 0px',
                    threshold: 0
                };

                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const id = entry.target.getAttribute('id');
                            navLinks.forEach(link => {
                                if (link.getAttribute('href') === `#${id}`) {
                                    link.classList.add('nav-link-active');
                                } else {
                                    link.classList.remove('nav-link-active');
                                }
                            });
                        }
                    });
                }, observerOptions);

                sections.forEach(section => observer.observe(section));
                console.log('Scrollspy inicializado correctamente');
            } catch (error) {
                console.error('Error al inicializar Scrollspy:', error);
            }
        },
        
        // Theme methods
        toggleTheme() {
            try {
                this.darkMode = !this.darkMode;
                console.log('Alternando tema a:', this.darkMode ? 'oscuro' : 'claro');
                if (this.darkMode) {
                    document.documentElement.classList.remove('light-theme');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.documentElement.classList.add('light-theme');
                    localStorage.setItem('theme', 'light');
                }
            } catch (error) {
                console.error('Error al alternar tema:', error);
            }
        },
        
        initTheme() {
            try {
                console.log('Inicializando tema...');
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'light' || (!savedTheme && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)) {
                    this.darkMode = false;
                    document.documentElement.classList.add('light-theme');
                } else {
                    this.darkMode = true;
                    document.documentElement.classList.remove('light-theme');
                }
            } catch (error) {
                console.error('Error al inicializar tema:', error);
            }
        },
        
        initDynamicPersonalization() {
            try {
                console.log('Inicializando personalización dinámica (DTR)...');
                const urlParams = new URLSearchParams(window.location.search);
                const sector = urlParams.get('sector') || urlParams.get('utm_campaign') || '';
                
                if (sector) {
                    const sectorLower = sector.toLowerCase();
                    if (sectorLower.includes('inmo') || sectorLower.includes('propiedad') || sectorLower.includes('realestate')) {
                        console.log('Personalización detectada: Sector Inmobiliario');
                        this.heroTitle = 'Multiplicá las ventas de tu Inmobiliaria con nuestro Agente IA de WhatsApp';
                        this.heroSubtitle = 'Automatizá respuestas a consultas de propiedades, agendamiento de visitas y seguimiento de leads las 24/7 sin esfuerzo.';
                        this.industryTab = 'inmo';
                        this.selectedService = 'whatsapp';
                        localStorage.setItem('selectedService', 'whatsapp');
                    } else if (sectorLower.includes('shop') || sectorLower.includes('ecom') || sectorLower.includes('ventas') || sectorLower.includes('store')) {
                        console.log('Personalización detectada: Sector E-commerce');
                        this.heroTitle = 'Maximizá la conversión de tu E-commerce con bots de IA';
                        this.heroSubtitle = 'Recuperá carritos abandonados, respondé preguntas frecuentes sobre envíos y stock, y vendé en automático por WhatsApp.';
                        this.industryTab = 'ecom';
                        this.selectedService = 'ia-atencion';
                        localStorage.setItem('selectedService', 'ia-atencion');
                    } else if (sectorLower.includes('serv') || sectorLower.includes('consult') || sectorLower.includes('prof') || sectorLower.includes('agenda')) {
                        console.log('Personalización detectada: Servicios / Profesionales');
                        this.heroTitle = 'Automatizá tu agenda de turnos y consultas con un Agente IA';
                        this.heroSubtitle = 'Ideal para consultorios, agencias y profesionales. Calificá prospectos y coordiná llamadas de forma proactiva y automatizada.';
                        this.industryTab = 'serv';
                        this.selectedService = 'sistemas';
                        localStorage.setItem('selectedService', 'sistemas');
                    }
                }
            } catch (error) {
                console.error('Error al inicializar personalización dinámica:', error);
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
if (window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.includes('.test') ||
    window.location.hostname.includes('.local')) {
    (function(originalFetch) {
        window.fetch = function(url, options) {
            return new Promise((resolve, reject) => {
                // Check if this is a webhook call
                if (url.includes('webhook')) {
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
                    // For non-webhook calls, use the original fetch
                    return originalFetch(url, options).then(resolve, reject);
                }
            });
        };
    })(window.fetch);
}
