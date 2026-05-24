import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Download, AlertTriangle, Filter, Plus, X, Check, Clock as ClockIcon } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { format } from 'date-fns';

const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 1000,
};

const modalContentStyle = {
  width: '100%',
  maxWidth: '500px',
  backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-color)',
  boxShadow: 'var(--shadow-lg)',
  padding: '2rem',
  position: 'relative',
};

export const ManagerDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState({
    peakOccupancy: 0,
    peakTime: '00:00',
    uniqueVehicles: 0,
    avgStay: '0.0',
    activeIncidents: 0,
  });
  const [chartData, setChartData] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [zones, setZones] = useState([]);
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newIncident, setNewIncident] = useState({
    plate: '',
    type: 'Mala lectura OCR',
    description: '',
    zoneId: '',
  });

  const fetchData = async () => {
    try {
      const startOfToday = new Date();
      startOfToday.setHours(0, 0, 0, 0);
      const todayIso = startOfToday.toISOString();

      // 1. Fetch Zones
      let maxCapacity = 50;
      const { data: zoneCapacityData, error: zoneErr } = await supabase
        .from('zonas')
        .select('id, nombre, capacidad');
        
      if (!zoneErr && zoneCapacityData) {
        setZones(zoneCapacityData);
        const amZone = zoneCapacityData.find(z => z.nombre === 'Aula Magna');
        if (amZone) maxCapacity = amZone.capacidad;
      }

      // 2. Fetch Accesses (para gráficos y KPIs)
      const { data: accesses, error: accessesError } = await supabase
        .from('accesos')
        .select('id, vehiculo_patente, fecha_entrada, fecha_salida')
        .or(`fecha_salida.is.null,fecha_entrada.gte.${todayIso},fecha_salida.gte.${todayIso}`);

      if (accessesError) throw accessesError;

      // Calcular tramos horarios (08:00 a 20:00)
      const hoursList = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'];
      const hourlyData = hoursList.map(hStr => {
        const [hours, minutes] = hStr.split(':').map(Number);
        const targetTime = new Date();
        targetTime.setHours(hours, minutes, 0, 0);

        let count = 0;
        if (accesses) {
          accesses.forEach(acc => {
            const entryTime = acc.fecha_entrada ? new Date(acc.fecha_entrada) : null;
            const exitTime = acc.fecha_salida ? new Date(acc.fecha_salida) : null;
            
            if (entryTime && entryTime <= targetTime) {
              if (!exitTime || exitTime > targetTime) {
                count++;
              }
            }
          });
        }
        return { time: hStr, ocupacion: count };
      });
      setChartData(hourlyData);

      // Ocupación Máxima (Pico del día)
      let maxOccupied = 0;
      let peakT = '08:00';
      hourlyData.forEach(pt => {
        if (pt.ocupacion > maxOccupied) {
          maxOccupied = pt.ocupacion;
          peakT = pt.time;
        }
      });
      const peakOccupancyPercentage = ((maxOccupied / maxCapacity) * 100).toFixed(1);

      // Vehículos Únicos hoy
      const todayEntries = accesses ? accesses.filter(acc => acc.fecha_entrada && new Date(acc.fecha_entrada) >= startOfToday) : [];
      const uniquePlates = new Set(todayEntries.map(acc => acc.vehiculo_patente));
      const totalUnique = uniquePlates.size;

      // Tiempo Promedio Estadía hoy
      const todayExits = accesses ? accesses.filter(acc => acc.fecha_salida && new Date(acc.fecha_salida) >= startOfToday) : [];
      let totalDurationMs = 0;
      let closedCount = 0;
      todayExits.forEach(acc => {
        if (acc.fecha_entrada && acc.fecha_salida) {
          const diff = new Date(acc.fecha_salida) - new Date(acc.fecha_entrada);
          totalDurationMs += diff;
          closedCount++;
        }
      });
      const averageStay = closedCount > 0 
        ? (totalDurationMs / closedCount / (1000 * 60 * 60)).toFixed(1) 
        : '0.0';

      // 3. Fetch Incidencias
      const { data: incidentsData, error: incidentsError } = await supabase
        .from('incidencias')
        .select('id, vehiculo_patente, tipo, descripcion, estado, fecha_creacion')
        .order('fecha_creacion', { ascending: false });

      if (incidentsError) throw incidentsError;

      setIncidents(incidentsData || []);

      const activeIncidents = incidentsData ? incidentsData.filter(inc => inc.estado !== 'cerrada').length : 0;

      setKpis({
        peakOccupancy: peakOccupancyPercentage,
        peakTime: peakT,
        uniqueVehicles: totalUnique,
        avgStay: averageStay,
        activeIncidents: activeIncidents,
      });

    } catch (err) {
      console.error('Error fetching manager dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Suscribirse a cambios en accesos e incidencias
    const accessesChannel = supabase.channel('manager:updates')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'accesos' }, () => {
        fetchData();
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'incidencias' }, () => {
        fetchData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(accessesChannel);
    };
  }, []);

  const handleUpdateStatus = async (incidentId, newStatus) => {
    try {
      const updateData = { estado: newStatus };
      if (newStatus === 'cerrada') {
        updateData.fecha_cierre = new Date().toISOString();
      } else {
        updateData.fecha_cierre = null;
      }
      
      const { error } = await supabase
        .from('incidencias')
        .update(updateData)
        .eq('id', incidentId);
        
      if (error) throw error;
      fetchData();
    } catch (err) {
      console.error('Error updating incident status:', err);
      alert('Error al actualizar el estado: ' + err.message);
    }
  };

  const handleCreateIncident = async (e) => {
    e.preventDefault();
    try {
      if (!newIncident.type || !newIncident.description) {
        alert('Por favor, completa los campos obligatorios.');
        return;
      }

      let plateUpper = null;
      if (newIncident.plate) {
        plateUpper = newIncident.plate.toUpperCase().trim();
        // Asegurar que la patente existe en la tabla de vehículos para evitar falla de clave foránea
        await supabase
          .from('vehiculos')
          .upsert([{ patente: plateUpper }]);
      }

      const { data: { user } } = await supabase.auth.getUser();

      const newInc = {
        vehiculo_patente: plateUpper,
        tipo: newIncident.type,
        descripcion: newIncident.description,
        zona_id: newIncident.zoneId ? parseInt(newIncident.zoneId) : null,
        usuario_id: user ? user.id : null,
        estado: 'abierta',
      };
      
      const { error } = await supabase
        .from('incidencias')
        .insert([newInc]);
        
      if (error) throw error;
      
      setIsModalOpen(false);
      setNewIncident({ plate: '', type: 'Mala lectura OCR', description: '', zoneId: '' });
      fetchData();
    } catch (err) {
      console.error('Error creating incident:', err);
      alert('Error al registrar la incidencia: ' + err.message);
    }
  };

  const exportReport = () => {
    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'ID,Patente,Tipo,Descripcion,Fecha,Estado\n';
    
    incidents.forEach(inc => {
      csvContent += `"${inc.id}","${inc.vehiculo_patente || 'N/A'}","${inc.tipo}","${inc.descripcion.replace(/"/g, '""')}","${inc.fecha_creacion}","${inc.estado}"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `reporte_incidencias_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex-center animate-pulse" style={{ height: '70vh', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Cargando datos ejecutivos y métricas...
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel Ejecutivo (Encargado)</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Estadísticas, KPIs y Gestión de Incidencias en tiempo real</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn btn-secondary" onClick={fetchData}>
            <Filter size={18} /> Actualizar
          </button>
          <button className="btn btn-primary" onClick={exportReport}>
            <Download size={18} /> Exportar Reporte
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Ocupación Máxima (Día)</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--ubb-blue)' }}>{kpis.peakOccupancy}%</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>A las {kpis.peakTime} hrs</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Total Vehículos Únicos</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--ubb-orange)' }}>{kpis.uniqueVehicles}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--status-success)' }}>Ingresos del día de hoy</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Tiempo Promedio Estadía</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{kpis.avgStay} hrs</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Basado en salidas registradas</p>
        </div>
        <div className="card" style={{ borderLeft: '4px solid var(--status-danger)' }}>
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Incidencias Activas</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--status-danger)' }}>{kpis.activeIncidents}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Abiertas o en revisión</p>
        </div>
      </div>

      {/* Charts */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem' }}>Curva de Ocupación Diaria</h2>
        <div style={{ height: '300px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
              <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} allowDecimals={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}
              />
              <Line type="monotone" dataKey="ocupacion" name="Vehículos" stroke="var(--ubb-blue)" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={20} color="var(--status-warning)" /> Gestión de Incidencias
          </h2>
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={18} /> Registrar Incidencia
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <th style={{ padding: '1rem 0.5rem' }}>ID</th>
                <th style={{ padding: '1rem 0.5rem' }}>Patente</th>
                <th style={{ padding: '1rem 0.5rem' }}>Tipo</th>
                <th style={{ padding: '1rem 0.5rem' }}>Descripción</th>
                <th style={{ padding: '1rem 0.5rem' }}>Fecha Registro</th>
                <th style={{ padding: '1rem 0.5rem' }}>Estado</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Acciones Rápidas</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc) => (
                <tr key={inc.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>#{inc.id}</td>
                  <td style={{ padding: '1rem 0.5rem', fontWeight: 600 }}>{inc.vehiculo_patente || 'N/A'}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>{inc.tipo}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>{inc.descripcion}</td>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>
                    {format(new Date(inc.fecha_creacion), 'dd-MM-yyyy HH:mm')}
                  </td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    <span className={`badge ${inc.estado === 'cerrada' ? 'badge-success' : inc.estado === 'en_revision' ? 'badge-warning' : 'badge-danger'}`}>
                      {inc.estado === 'cerrada' ? 'Resuelto' : inc.estado === 'en_revision' ? 'En Revisión' : 'Abierto'}
                    </span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      {inc.estado === 'abierta' && (
                        <>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '2px' }}
                            onClick={() => handleUpdateStatus(inc.id, 'en_revision')}
                          >
                            <ClockIcon size={12} /> Revisar
                          </button>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: '2px' }}
                            onClick={() => handleUpdateStatus(inc.id, 'cerrada')}
                          >
                            <Check size={12} /> Resolver
                          </button>
                        </>
                      )}
                      {inc.estado === 'en_revision' && (
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: '2px' }}
                          onClick={() => handleUpdateStatus(inc.id, 'cerrada')}
                        >
                          <Check size={12} /> Resolver
                        </button>
                      )}
                      {inc.estado === 'cerrada' && (
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}
                          onClick={() => handleUpdateStatus(inc.id, 'abierta')}
                        >
                          Reabrir
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {incidents.length === 0 && (
                <tr>
                  <td colSpan="7" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No hay incidencias registradas.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal para Crear Incidencia */}
      {isModalOpen && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Registrar Nueva Incidencia</h3>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleCreateIncident} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Patente (Opcional)</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="Ej. CRJC39"
                  value={newIncident.plate}
                  onChange={(e) => setNewIncident(prev => ({ ...prev, plate: e.target.value }))}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Tipo de Incidencia *</label>
                <select 
                  className="input-field"
                  value={newIncident.type}
                  onChange={(e) => setNewIncident(prev => ({ ...prev, type: e.target.value }))}
                  required
                >
                  <option value="Mala lectura OCR">Mala lectura OCR</option>
                  <option value="Vehículo mal estacionado">Vehículo mal estacionado</option>
                  <option value="Acceso no autorizado">Acceso no autorizado</option>
                  <option value="Obstáculo en vía">Obstáculo en vía</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Zona Asociada (Opcional)</label>
                <select 
                  className="input-field"
                  value={newIncident.zoneId}
                  onChange={(e) => setNewIncident(prev => ({ ...prev, zoneId: e.target.value }))}
                >
                  <option value="">Seleccionar zona...</option>
                  {zones.map(z => (
                    <option key={z.id} value={z.id}>{z.nombre}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Descripción de la Incidencia *</label>
                <textarea 
                  className="input-field" 
                  rows="3"
                  placeholder="Detalles de la incidencia observada..."
                  value={newIncident.description}
                  onChange={(e) => setNewIncident(prev => ({ ...prev, description: e.target.value }))}
                  required
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Registrar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
