import { defineConfig } from 'vite'
import { resolve } from 'path'

const assetBaseUrl = process.env.ASSET_BASE_URL || '/'
const normalizedBase = assetBaseUrl.endsWith('/') ? assetBaseUrl : `${assetBaseUrl}/`

export default defineConfig({
  root: 'src',
  publicDir: '../public',
  base: normalizedBase,

  build: {
    cssCodeSplit: false,
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'assets/style-[hash][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
      input: {
        main: resolve(__dirname, 'src/index.html'),
        login: resolve(__dirname, 'src/login.html'),
        register: resolve(__dirname, 'src/register.html'),
        admin_invites: resolve(__dirname, 'src/admin-invites.html'),
      }
    }
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
