export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  ssr: false,
  css: ['~/assets/main.css'],
  runtimeConfig: {
    public: {
      // Overridden at runtime by the NUXT_PUBLIC_API_BASE environment variable
      // (see .env locally, project env vars on Vercel). Nuxt maps
      // NUXT_PUBLIC_<KEY> onto runtimeConfig.public.<key> automatically.
      apiBase: ''
    }
  },
  app: {
    head: {
      title: 'Momentum board',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#0c1117' }
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap'
        }
      ],
      // Apply the persisted / system theme before first paint to avoid a flash.
      script: [
        {
          innerHTML:
            "(function(){try{var t=localStorage.getItem('momentum-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.dataset.theme=t;}catch(e){}})();",
          tagPosition: 'head'
        }
      ]
    }
  }
})
