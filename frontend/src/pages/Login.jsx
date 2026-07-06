import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogIn, AlertCircle } from 'lucide-react';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error } = await signIn(email, password);
      if (error) throw error;
      navigate('/dashboard/guardia'); // Default redirect, protected route will handle unauthorized
    } catch (err) {
      console.error(err);
      const msg = err.message === 'Invalid login credentials'
        ? 'Email y/o contraseña incorrectos'
        : err.message === 'Usuario inactivo'
        ? 'Tu cuenta ha sido desactivada. Comunícate con el administrador.'
        : (err.message || 'Error al iniciar sesión');
      setError(msg);
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="flex-center" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)', padding: '1rem' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ color: 'var(--ubb-blue)', fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Gestión estacionamiento</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Ingreso para personal autorizado</p>
        </div>

        {error && (
          <div className="badge-danger" style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem'
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Correo</label>
            <input
              type="email"
              className="input-field"
              placeholder="usuario@ubiobio.cl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Contraseña</label>
            <input
              type="password"
              className="input-field"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
            {loading ? 'Cargando...' : <><LogIn size={18} /> Iniciar Sesión</>}
          </button>
        </form>


      </div>
    </div>
  );
};
      
