import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../../config/www/dxsafety-card',
    lib: {
      entry: resolve(__dirname, 'src/dxsafety-card.tsx'),
      name: 'DXSafetyCard',
      fileName: 'dxsafety-card',
      formats: ['es']
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        }
      }
    }
  }
})
