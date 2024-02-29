module.exports = {
    /**
     * Application configuration section
     * http://pm2.keymetrics.io/docs/usage/application-declaration/
     * pm2 deploy ecosystem.config.js development setup
     * pm2 deploy ecosystem.config.js development update
     * pm2 deploy development update
     * pm2 deploy development exec "pm2 restart all"
     */
    apps: [
        {
            name: 'speech-to-text-translation',
            script: 'gunicorn',
            args: '--bind 0.0.0.0:7500 main:app',
            instances: 1,
            autorestart: true,
            interpreter: 'python3',
            max_memory_restart: '256M',
            env: {
                NODE_ENV: 'development',
            },
        },
    ],

    /**
     * Deployment section
     * http://pm2.keymetrics.io/docs/usage/deployment/
     */
    
};