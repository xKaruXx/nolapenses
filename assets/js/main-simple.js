/**
 * Simplified JavaScript for No La Penses! Landing Page
 * Focusing only on mood buttons functionality
 */

// Initialize Alpine.js data directly without waiting for DOMContentLoaded
// This ensures Alpine.js can access our functions as soon as it initializes
window.landingApp = function() {
    return {
        // AI state
        aiMood: '',
        aiGreeting: '',
        
        // User mood state
        userMood: '',
        userMoodEmoji: '',
        userMoodResponse: '',
        
        // Form data
        form: {
            estado_animo: ''
        },
        
        // Browser info for analytics
        browserInfo: {
            name: '',
            time: ''
        },
        
        // Initialize the app
        init() {
            console.log('App initialized');
            
            // Make sure CONFIG is loaded
            if (typeof CONFIG === 'undefined') {
                console.error('Error: CONFIG object is not defined. Make sure config.js is loaded before main.js');
                return;
            }
            
            // Set browser info
            this.browserInfo = {
                name: this.getBrowserName(),
                time: new Date().toLocaleTimeString()
            };
            
            // Set random AI mood
            this.setRandomAIMood();
            
            console.log('Initialization complete');
        },
        
        // Set a random AI mood on page load
        setRandomAIMood() {
            try {
                console.log('Setting random AI mood');
                
                if (!CONFIG.aiMoods || !Array.isArray(CONFIG.aiMoods) || CONFIG.aiMoods.length === 0) {
                    console.error('CONFIG.aiMoods is not properly defined');
                    this.aiMood = 'alegre';
                    this.aiGreeting = '¡Hola! ¿En qué puedo ayudarte hoy?';
                    return;
                }
                
                const randomIndex = Math.floor(Math.random() * CONFIG.aiMoods.length);
                const selectedMood = CONFIG.aiMoods[randomIndex];
                
                this.aiMood = selectedMood.mood;
                this.aiGreeting = selectedMood.greeting;
                
                console.log('AI mood set to:', this.aiMood);
                console.log('AI greeting set to:', this.aiGreeting);
            } catch (error) {
                console.error('Error setting random AI mood:', error);
                this.aiMood = 'alegre';
                this.aiGreeting = '¡Hola! ¿En qué puedo ayudarte hoy?';
            }
        },
        
        // Handle user mood selection
        setUserMood(mood, emoji) {
            try {
                console.log('User selected mood:', mood, emoji);
                
                this.userMood = mood;
                this.userMoodEmoji = emoji;
                this.form.estado_animo = mood;
                
                // Set initial response from CONFIG if available
                if (CONFIG.userMoodResponses && CONFIG.userMoodResponses[mood]) {
                    this.userMoodResponse = CONFIG.userMoodResponses[mood];
                } else {
                    this.userMoodResponse = 'Gracias por compartir cómo te sentís hoy.';
                }
                
                console.log('Initial user mood response:', this.userMoodResponse);
                
                // Simulate personalized greeting (local environment simulation)
                setTimeout(() => {
                    this.getPersonalizedGreeting(mood);
                }, 500);
            } catch (error) {
                console.error('Error setting user mood:', error);
                this.userMoodResponse = 'Gracias por compartir cómo te sentís hoy.';
            }
        },
        
        // Get personalized greeting based on user mood
        getPersonalizedGreeting(mood) {
            try {
                console.log('Getting personalized greeting for mood:', mood);
                
                // Show loading state
                this.userMoodResponse = 'Procesando tu estado de ánimo...';
                
                // Simulated personalized greetings based on mood
                const simulatedResponses = {
                    'Alegre': `¡Qué buena onda que estés re contento! ${this.aiMood === 'alegre' ? 'Yo también estoy re arriba hoy.' : 'Me contagiás tu buena onda.'} ¿Querés que te cuente qué podemos hacer por vos?`,
                    'Creativo': `¡Banco fuerte tu creatividad! ${this.aiMood === 'creativo' ? 'Hoy estamos re inspirados los dos.' : 'Me encanta charlar con gente creativa.'} ¿Te gustaría ver algunos de nuestros proyectos más creativos?`,
                    'Energético': `¡Estás a mil! ${this.aiMood === 'energético' ? 'Yo también estoy re manija hoy.' : 'Se nota que venís con toda la energía.'} Con esa actitud, podemos hacer altas cosas juntos.`,
                    'Curioso': `¡Qué bueno que seas chusma! ${this.aiMood === 'curioso' ? 'Yo también soy re metido.' : 'La curiosidad es clave para descubrir cosas nuevas.'} ¿Querés que te cuente más sobre lo que hacemos?`,
                    'Motivado': `¡Esa es la actitud! ${this.aiMood === 'motivado' ? 'Hoy estamos los dos con todas las pilas.' : 'Se nota que venís con ganas de hacer cosas.'} Vamos a romperla toda con tu proyecto.`
                };
                
                // Update the response with simulated greeting after a short delay
                setTimeout(() => {
                    this.userMoodResponse = simulatedResponses[mood] || CONFIG.userMoodResponses[mood];
                    console.log('Updated user mood response:', this.userMoodResponse);
                }, 1000);
            } catch (error) {
                console.error('Error getting personalized greeting:', error);
                this.userMoodResponse = CONFIG.userMoodResponses[mood] || 'Gracias por compartir cómo te sentís hoy.';
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
                console.error('Error getting browser name:', error);
                return 'Unknown';
            }
        }
    };
};

// Add a console log to verify the script is loaded
console.log('main-simple.js loaded successfully');

// Log CONFIG object to verify it's available
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    console.log('CONFIG object:', CONFIG);
});
