import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Car, Clock, ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

export const PublicStatus = () => {
  const [occupancy, setOccupancy] = useState({ current: 0, max: 130 }); // Mock default max 130
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        // Llamar a la función segura RPC
        const { data, error } = await supabase
          .rpc('obtener_ocupacion_publica');
          
        if (!error && data && data.length > 0) {
          const stats = data[0];
          setOccupancy({
            current: stats.ocupados_totales,
            max: stats.capacidad_total
          });
        }
      } catch (err) {
        console.error('Error fetching occupancy:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();

    const channel = supabase.channel('public:accesos')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'accesos' }, () => {
        fetchStatus();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const availableSpots = Math.max(0, occupancy.max - occupancy.current);
  const occupancyPercentage = (occupancy.current / occupancy.max) * 100;
  
  let statusColor = 'var(--status-success)';
  let statusText = 'Disponible';
  
  if (occupancyPercentage > 90) { // 91% - 100%
    statusColor = 'var(--status-danger)';
    statusText = 'Lleno';
  } else if (occupancyPercentage > 75) { // 76% - 90%
    statusColor = 'var(--ubb-orange)';
    statusText = 'Alta Ocupación';
  } else if (occupancyPercentage > 50) { // 51% - 75%
    statusColor = 'var(--status-warning)';
    statusText = 'Ocupación Media';
  }
  // Circular progress calculations
  const radius = 108;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (occupancyPercentage / 100) * circumference;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)', display: 'flex', flexDirection: 'column' }}>
      {/* Header Corporativo */}
      <header style={{ backgroundColor: 'var(--ubb-blue)', padding: '1rem', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <img 
            src="/logoUBB2.png" 
            alt="Logo UBB" 
            style={{ height: '40px', width: 'auto' }} 
          />
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Universidad del Bío-Bío</h1>
            <p style={{ fontSize: '0.875rem', opacity: 0.8, margin: 0 }}>Campus Fernando May</p>
          </div>
        </div>
        <Link to="/login" style={{ color: 'white', textDecoration: 'none', fontSize: '0.875rem', opacity: 0.8 }}>Acceso Personal</Link>
      </header>

      {/* Contenido Principal */}
      <main className="container" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '2rem 1rem' }}>
        <div className="glass-panel animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%', padding: '3rem 2rem', textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.5rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Estado del Estacionamiento</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '3rem' }}>Sector Aula Magna</p>

          {loading ? (
            <div className="animate-pulse" style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Obteniendo información en tiempo real...</p>
            </div>
          ) : (
            <>
              {/* Indicador Principal */}
              <div style={{ position: 'relative', width: '240px', height: '240px', margin: '0 auto 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                {/* SVG Circular Progress */}
                <svg width="240" height="240" style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}>
                  <circle 
                    cx="120" cy="120" r={radius}
                    fill="transparent"
                    stroke="var(--border-color)"
                    strokeWidth="12"
                  />
                  <circle 
                    cx="120" cy="120" r={radius}
                    fill="transparent"
                    stroke={statusColor}
                    strokeWidth="12"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease-in-out, stroke 0.5s ease' }}
                  />
                </svg>
                
                {/* Contenido Central */}
                <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'center', filter: `drop-shadow(0 0 20px ${statusColor}40)` }}>
                  <span style={{ fontSize: '4rem', fontWeight: 800, color: statusColor, lineHeight: 1 }}>{availableSpots}</span>
                  <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 500, marginTop: '0.5rem' }}>CUPOS LIBRES</span>
                </div>
              </div>

              <div style={{ display: 'inline-block', padding: '0.5rem 1.5rem', borderRadius: '9999px', backgroundColor: `${statusColor}20`, color: statusColor, fontWeight: 700, fontSize: '1.25rem', marginBottom: '2rem' }}>
                {statusText}
              </div>

              {/* Info Extra */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'left' }}>
                <div className="card" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <Car size={24} color="var(--ubb-blue)" />
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>Ocupación</p>
                    <p style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{occupancy.current} / {occupancy.max}</p>
                  </div>
                </div>
                <div className="card" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <Clock size={24} color="var(--text-primary)" />
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>Actualizado</p>
                    <p style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Hace instantes</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      <footer style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        <p>Sistema de Apoyo a la Gestión de Estacionamientos &copy; {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
};
