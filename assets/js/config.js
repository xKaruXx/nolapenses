/**
 * Configuration file for No La Penses! Landing Page
 * Contains webhook URLs and other configuration settings
 */

const CONFIG = {
    // Webhook URLs for n8n integrations
    webhooks: {
        // Generic webhook used by mood/service selection flows
        mood: 'https://n8n.nolapenses.com.ar/webhook-test/web-nolapenses',

        // Webhook for user mood state
        userMood: 'https://n8n.nolapenses.com.ar/webhook-test/web-nolapenses',
        
        // Webhook for audio processing
        audioReceived: 'https://n8n.nolapenses.com.ar/webhook/audio-recibido',
        
        // Webhook for new lead form submission
        newLead: 'https://n8n.nolapenses.com.ar/webhook/lead-nuevo'
    },
    
    // WhatsApp contact information
    whatsapp: {
        contactUrl: 'https://wa.me/5492665267159'
    },
    
    // AI mood settings
    aiMoods: [
        { mood: 'alegre', emoji: '😄', greeting: '¡Qué buena onda que nos visites! Re copado mostrarte todo lo que podemos hacer por vos.' },
        { mood: 'creativo', emoji: '🎨', greeting: 'Tengo una banda de ideas para tu proyecto. ¿Nos ponemos las pilas juntos?' },
        { mood: 'energético', emoji: '⚡', greeting: '¡Estoy a mil! Listo para automatizar tus cosas y hacerte la vida más fácil.' },
        { mood: 'motivado', emoji: '💪', greeting: 'Hoy está picando para transformar tu negocio con soluciones digitales que son un viaje.' },
        { mood: 'curioso', emoji: '🤔', greeting: 'Me re copa saber más de tu proyecto. ¿Me tirás la data de lo que tenés en mente?' }
    ],
    
    // User mood response templates
    userMoodResponses: {
        'Alegre': '¡Qué buena onda verte tan contento! Es el momento justo para mandarnos a hacer cosas nuevas.',
        'Creativo': 'La creatividad es lo más. ¡Tenemos todas las herramientas para darle vida a tus ideas más locas!',
        'Energético': '¡Con esa manija que tenés podemos hacer cualquier cosa! Nuestras automatizaciones te van a ayudar a seguir a full.',
        'Curioso': 'Ser chusma está buenísimo para descubrir cosas nuevas. Te invito a que chusmees todo lo que podemos hacer por vos.',
        'Motivado': '¡Golazo! Con tus ganas y nuestras soluciones, vamos a romperla toda.'
    }
};
