import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Manejo de errores global para depuración en el cliente
window.addEventListener('error', (event) => {
  alert('Error de React/JS: ' + event.message + '\nEn: ' + event.filename + ':' + event.lineno + '\nStack: ' + (event.error?.stack || 'no stack'));
});
window.addEventListener('unhandledrejection', (event) => {
  alert('Promesa rechazada no manejada: ' + event.reason);
});

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
