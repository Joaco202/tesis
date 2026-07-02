import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Download, AlertTriangle, Filter, Plus, X, Check, Clock as ClockIcon, Car, Search, Calendar as CalendarIcon, ChevronLeft, ChevronRight, RotateCw } from 'lucide-react';
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

const CustomDatePicker = ({ label, value, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Current view year & month (default to value's month/year or current date)
  const today = new Date();
  const initialDate = value ? new Date(value + 'T00:00:00') : today;
  const [viewYear, setViewYear] = useState(initialDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(initialDate.getMonth()); // 0-indexed
  const [slideDirection, setSlideDirection] = useState('next');
  const [isHovered, setIsHovered] = useState(false);

  // Format value to display (dd/MM/yyyy)
  const displayValue = value 
    ? format(new Date(value + 'T00:00:00'), 'dd/MM/yyyy') 
    : format(new Date(), 'dd/MM/yyyy');

  // Get number of days in the month
  const getDaysInMonth = (year, month) => {
    return new Date(year, month + 1, 0).getDate();
  };

  // Get weekday of the 1st of the month (0 = Sunday, 1 = Monday, etc.)
  const getFirstDayOfMonth = (year, month) => {
    return new Date(year, month, 1).getDay();
  };

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth);

  const monthsSpanish = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const handlePrevMonth = () => {
    setSlideDirection('prev');
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(prev => prev - 1);
    } else {
      setViewMonth(prev => prev - 1);
    }
  };

  const handleNextMonth = () => {
    setSlideDirection('next');
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(prev => prev + 1);
    } else {
      setViewMonth(prev => prev + 1);
    }
  };

  const handleSelectDay = (day) => {
    const monthStr = String(viewMonth + 1).padStart(2, '0');
    const dayStr = String(day).padStart(2, '0');
    const newDateStr = `${viewYear}-${monthStr}-${dayStr}`;
    onChange(newDateStr);
    setIsOpen(false);
  };

  // Check if a day is the selected value
  const isSelected = (day) => {
    if (!value) return false;
    const dateObj = new Date(value + 'T00:00:00');
    return (
      dateObj.getFullYear() === viewYear &&
      dateObj.getMonth() === viewMonth &&
      dateObj.getDate() === day
    );
  };

  // Check if a day is today
  const isToday = (day) => {
    return (
      today.getFullYear() === viewYear &&
      today.getMonth() === viewMonth &&
      today.getDate() === day
    );
  };

  // Build grid
  const cells = [];
  // Empty cells for offset
  for (let i = 0; i < firstDay; i++) {
    cells.push(<div key={`empty-${i}`} style={{ width: '32px', height: '32px' }} />);
  }
  // Day cells
  for (let d = 1; d <= daysInMonth; d++) {
    const selected = isSelected(d);
    const todayCell = isToday(d);
    
    cells.push(
      <button
        key={`day-${d}`}
        type="button"
        onClick={() => handleSelectDay(d)}
        style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          border: 'none',
          background: selected ? 'var(--ubb-blue)' : todayCell ? 'var(--ubb-blue)' : 'none',
          color: selected ? '#ffffff' : todayCell ? '#ffffff' : 'var(--text-primary)',
          fontWeight: selected || todayCell ? '600' : 'normal',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '0.875rem',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          if (!selected && !todayCell) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        }}
        onMouseLeave={(e) => {
          if (!selected && !todayCell) e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
        {d}
      </button>
    );
  }

  // Close when clicking outside
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="custom-datepicker-container" style={{ position: 'relative', flex: '0 0 220px', marginTop: '6px' }}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{ 
          height: '42px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          padding: '0 1rem', 
          cursor: 'pointer',
          userSelect: 'none',
          border: (isOpen || isHovered) ? '1px solid #ffffff' : '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--bg-secondary)',
          position: 'relative',
          transition: 'all 0.2s ease',
        }}
      >
        {/* Floating Label */}
        <span 
          style={{ 
            position: 'absolute', 
            top: '-9px', 
            left: '12px', 
            backgroundColor: 'var(--bg-secondary)', 
            padding: '0 6px', 
            fontSize: '0.75rem', 
            fontWeight: 500,
            color: (isOpen || isHovered) ? 'var(--text-primary)' : 'var(--text-secondary)',
            pointerEvents: 'none',
            transition: 'color 0.2s ease',
          }}
        >
          {label}
        </span>
        <span style={{ color: 'var(--text-primary)', fontSize: '0.875rem' }}>
          {displayValue}
        </span>
        <CalendarIcon size={16} style={{ color: 'var(--text-secondary)' }} />
      </div>

      {isOpen && (
        <div 
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            zIndex: 1000,
            width: '280px',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '1rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
              {monthsSpanish[viewMonth]} {viewYear}
            </span>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <button 
                type="button" 
                onClick={handlePrevMonth}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <ChevronLeft size={16} />
              </button>
              <button 
                type="button" 
                onClick={handleNextMonth}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          {/* Days of week */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 32px)', gap: '4px', justifyContent: 'center' }}>
            {['D', 'L', 'M', 'M', 'J', 'V', 'S'].map((day, idx) => (
              <div 
                key={idx} 
                style={{ 
                  fontSize: '0.75rem', 
                  fontWeight: 600, 
                  color: 'var(--text-secondary)', 
                  width: '32px', 
                  height: '32px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}
              >
                {day}
              </div>
            ))}
          </div>

          {/* Days grid */}
          <div style={{ overflow: 'hidden', width: '100%' }}>
            <div 
              key={`${viewYear}-${viewMonth}`}
              className={slideDirection === 'next' ? 'slide-in-right' : 'slide-in-left'}
              style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 32px)', gap: '4px', justifyContent: 'center' }}
            >
              {cells}
            </div>
          </div>
        </div>
      )}
    </div>
  );
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
  
  // Vehicle management states
  const [vehicles, setVehicles] = useState([]);
  const [searchVehicle, setSearchVehicle] = useState('');
  const [isVehicleModalOpen, setIsVehicleModalOpen] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [vehicleForm, setVehicleForm] = useState({
    patente: '',
    propietario_nombre: '',
    tipo: 'Automóvil',
    funcionario: true,
    observaciones: '',
  });
  const [submittingVehicle, setSubmittingVehicle] = useState(false);
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newIncident, setNewIncident] = useState({
    plate: '',
    description: '',
    zoneId: '',
  });
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingIncident, setEditingIncident] = useState(null);

  // Pagination states
  const [vehiclePageSize, setVehiclePageSize] = useState(20);
  const [vehicleCurrentPage, setVehicleCurrentPage] = useState(1);
  const [incidentPageSize, setIncidentPageSize] = useState(20);
  const [incidentCurrentPage, setIncidentCurrentPage] = useState(1);

  // Access report date filters
  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const [accessStartDate, setAccessStartDate] = useState(todayStr);
  const [accessEndDate, setAccessEndDate] = useState(todayStr);
  const [exportingAccess, setExportingAccess] = useState(false);

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

      // Calcular tramos horarios (07:00 a 19:00)
      const hoursList = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];
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
      let peakT = '07:00';
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

      // 4. Fetch Vehicles
      const { data: vehiclesData, error: vehiclesError } = await supabase
        .from('vehiculos')
        .select('*')
        .order('created_at', { ascending: false });

      if (!vehiclesError && vehiclesData) {
        setVehicles(vehiclesData);
      }

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

    // Suscribirse a cambios en accesos, incidencias y vehículos
    const updatesChannel = supabase.channel('manager:updates')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'accesos' }, () => {
        fetchData();
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'incidencias' }, () => {
        fetchData();
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'vehiculos' }, () => {
        fetchData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(updatesChannel);
    };
  }, []);

  const handleOpenEditModal = (inc) => {
    setEditingIncident({
      id: inc.id,
      vehiculo_patente: inc.vehiculo_patente || '',
      descripcion: inc.descripcion || '',
      estado: inc.estado === 'cerrada' ? 'cerrada' : 'abierta',
      zona_id: inc.zona_id || '',
    });
    setIsEditModalOpen(true);
  };

  const handleSaveEditIncident = async (e) => {
    e.preventDefault();
    if (!editingIncident.descripcion.trim()) {
      alert('Por favor, completa la descripción.');
      return;
    }
    try {
      const { error } = await supabase
        .from('incidencias')
        .update({
          descripcion: editingIncident.descripcion.trim(),
          estado: editingIncident.estado,
          zona_id: editingIncident.zona_id ? parseInt(editingIncident.zona_id) : null,
        })
        .eq('id', editingIncident.id);

      if (error) throw error;
      setIsEditModalOpen(false);
      setEditingIncident(null);
      fetchData();
    } catch (err) {
      console.error('Error updating incident:', err);
      alert('Error al guardar cambios de la incidencia: ' + err.message);
    }
  };

  const handleDeleteIncident = async (incidentId) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar esta incidencia?')) {
      return;
    }
    try {
      const { error } = await supabase
        .from('incidencias')
        .delete()
        .eq('id', incidentId);

      if (error) throw error;
      fetchData();
    } catch (err) {
      console.error('Error deleting incident:', err);
      alert('Error al eliminar la incidencia: ' + err.message);
    }
  };

  const handleCreateIncident = async (e) => {
    e.preventDefault();
    try {
      if (!newIncident.description) {
        alert('Por favor, completa la descripción.');
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
        tipo: 'Incidencia',
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
      setNewIncident({ plate: '', description: '', zoneId: '' });
      fetchData();
    } catch (err) {
      console.error('Error creating incident:', err);
      alert('Error al registrar la incidencia: ' + err.message);
    }
  };

  const handleOpenVehicleModal = (veh = null) => {
    if (veh) {
      setSelectedVehicle(veh);
      setVehicleForm({
        patente: veh.patente,
        propietario_nombre: veh.propietario_nombre || '',
        tipo: veh.tipo || 'Automóvil',
        funcionario: veh.funcionario,
        observaciones: veh.observaciones || '',
      });
    } else {
      setSelectedVehicle(null);
      setVehicleForm({
        patente: '',
        propietario_nombre: '',
        tipo: 'Automóvil',
        funcionario: true,
        observaciones: '',
      });
    }
    setIsVehicleModalOpen(true);
  };

  const handleSaveVehicle = async (e) => {
    e.preventDefault();
    if (!vehicleForm.patente.trim() || !vehicleForm.propietario_nombre.trim()) {
      alert('Por favor, completa la patente y el nombre del funcionario.');
      return;
    }

    setSubmittingVehicle(true);
    try {
      const normalizedPlate = vehicleForm.patente.trim().toUpperCase();
      
      const vehiclePayload = {
        patente: normalizedPlate,
        propietario_nombre: vehicleForm.propietario_nombre.trim(),
        tipo: vehicleForm.tipo,
        funcionario: vehicleForm.funcionario,
        observaciones: vehicleForm.observaciones.trim() || null,
      };

      const { error } = await supabase
        .from('vehiculos')
        .upsert([vehiclePayload]);

      if (error) throw error;

      alert('Vehículo guardado y vinculado correctamente.');
      setIsVehicleModalOpen(false);
      setSelectedVehicle(null);
      fetchData();
    } catch (err) {
      console.error('Error saving vehicle:', err);
      alert('Error al vincular el vehículo: ' + err.message);
    } finally {
      setSubmittingVehicle(false);
    }
  };

  const exportReport = () => {
    let csvContent = 'data:text/csv;charset=utf-8,\uFEFF';
    csvContent += 'ID,Patente,Descripcion,Fecha,Estado\n';
    
    incidents.forEach(inc => {
      csvContent += `"${inc.id}","${inc.vehiculo_patente || 'N/A'}","${inc.descripcion.replace(/"/g, '""')}","${inc.fecha_creacion}","${inc.estado}"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `reporte_incidencias_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportAccessReport = async () => {
    setExportingAccess(true);
    try {
      let query = supabase
        .from('accesos')
        .select('id, vehiculo_patente, camera_id, fecha_entrada, confianza_ocr, fecha_salida, camera_salida_id, confianza_ocr_salida')
        .order('fecha_entrada', { ascending: false });

      if (accessStartDate) {
        const start = new Date(accessStartDate);
        start.setHours(0, 0, 0, 0);
        query = query.gte('fecha_entrada', start.toISOString());
      }
      if (accessEndDate) {
        const end = new Date(accessEndDate);
        end.setHours(23, 59, 59, 999);
        query = query.lte('fecha_entrada', end.toISOString());
      }

      const { data, error } = await query;
      if (error) throw error;

      if (!data || data.length === 0) {
        alert('No se encontraron registros de accesos en el rango seleccionado.');
        return;
      }

      let csvContent = '\uFEFF'; // UTF-8 BOM
      csvContent += 'ID,Patente,Camara Entrada,Fecha Entrada,Confianza Entrada,Fecha Salida,Camara Salida,Confianza Salida\n';
      
      data.forEach(acc => {
        const fEntrada = acc.fecha_entrada ? format(new Date(acc.fecha_entrada), 'yyyy-MM-dd HH:mm:ss') : '';
        const fSalida = acc.fecha_salida ? format(new Date(acc.fecha_salida), 'yyyy-MM-dd HH:mm:ss') : '';
        const confEntrada = acc.confianza_ocr ? `${(acc.confianza_ocr * 100).toFixed(1)}%` : '';
        const confSalida = acc.confianza_ocr_salida ? `${(acc.confianza_ocr_salida * 100).toFixed(1)}%` : '';
        
        csvContent += `"${acc.id}","${acc.vehiculo_patente}","${acc.camera_id || ''}","${fEntrada}","${confEntrada}","${fSalida}","${acc.camera_salida_id || ''}","${confSalida}"\n`;
      });

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      
      const startStr = accessStartDate || 'inicio';
      const endStr = accessEndDate || 'fin';
      link.setAttribute('download', `reporte_accesos_${startStr}_a_${endStr}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error exporting access logs:', err);
      alert('Error al exportar registros: ' + err.message);
    } finally {
      setExportingAccess(false);
    }
  };

  const exportVehiclesReport = () => {
    let csvContent = '\uFEFF'; // UTF-8 BOM para soporte directo de Excel en español
    csvContent += 'Patente,Propietario,Observaciones,Fecha Registro\n';
    
    vehicles.forEach(veh => {
      const fRegistro = veh.created_at ? format(new Date(veh.created_at), 'yyyy-MM-dd HH:mm:ss') : '';
      csvContent += `"${veh.patente}","${veh.propietario_nombre || ''}","${(veh.observaciones || '').replace(/"/g, '""')}","${fRegistro}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `reporte_patentes_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Pagination computations for Vehicles
  const filteredVehicles = vehicles.filter(veh => 
    veh.patente.toLowerCase().includes(searchVehicle.toLowerCase()) ||
    (veh.propietario_nombre && veh.propietario_nombre.toLowerCase().includes(searchVehicle.toLowerCase()))
  );
  const totalVehiclesCount = filteredVehicles.length;
  const totalVehiclePages = Math.ceil(totalVehiclesCount / vehiclePageSize) || 1;
  const paginatedVehicles = filteredVehicles.slice(
    (vehicleCurrentPage - 1) * vehiclePageSize,
    vehicleCurrentPage * vehiclePageSize
  );

  // Pagination computations for Incidents
  const totalIncidentsCount = incidents.length;
  const totalIncidentPages = Math.ceil(totalIncidentsCount / incidentPageSize) || 1;
  const paginatedIncidents = incidents.slice(
    (incidentCurrentPage - 1) * incidentPageSize,
    incidentCurrentPage * incidentPageSize
  );

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
    <>
      <div className="animate-fade-in">
        <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel Ejecutivo (Encargado)</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Estadísticas, KPIs y Gestión de Incidencias en tiempo real</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn btn-secondary" onClick={fetchData}>
            <RotateCw size={18} /> Actualizar
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
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{kpis.peakOccupancy}%</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>A las {kpis.peakTime} hrs</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Total Vehículos Únicos</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{kpis.uniqueVehicles}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Ingresos del día de hoy</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Tiempo Promedio Estadía</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{kpis.avgStay} hrs</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Basado en salidas registradas</p>
        </div>
        <div className="card" style={{ borderLeft: '4px solid var(--status-danger)' }}>
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Incidencias Activas</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{kpis.activeIncidents}</p>
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

      {/* Exportador de Accesos Históricos */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Download size={20} color="var(--ubb-blue)" /> Exportador Histórico de Accesos
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
          Selecciona un rango de fechas para consultar y descargar el historial completo de ingresos y egresos de vehículos en formato CSV.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'flex-end' }}>
          <CustomDatePicker 
            label="Desde" 
            value={accessStartDate} 
            onChange={setAccessStartDate} 
          />
          <CustomDatePicker 
            label="Hasta" 
            value={accessEndDate} 
            onChange={setAccessEndDate} 
          />
          <div style={{ flex: '0 0 auto' }}>
            <button 
              className="btn btn-primary" 
              onClick={exportAccessReport}
              disabled={exportingAccess}
              style={{ minWidth: '180px', height: '42px' }}
            >
              <Download size={18} /> {exportingAccess ? 'Exportando...' : 'Descargar Historial'}
            </button>
          </div>
        </div>
      </div>

      {/* Gestión de Vehículos y Funcionarios */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Car size={20} color="var(--ubb-blue)" /> Gestión de Vehículos y Patentes
          </h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Mostrar:</span>
              <select
                className="input-field"
                style={{ width: '75px', height: '38px', padding: '0 0.5rem' }}
                value={vehiclePageSize}
                onChange={(e) => {
                  setVehiclePageSize(Number(e.target.value));
                  setVehicleCurrentPage(1);
                }}
              >
                <option value={20}>20</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </div>
            <div style={{ position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input 
                type="text" 
                placeholder="Buscar propietario o patente..." 
                className="input-field" 
                style={{ paddingLeft: '2.5rem', width: '250px', height: '38px' }}
                value={searchVehicle}
                onChange={(e) => {
                  setSearchVehicle(e.target.value);
                  setVehicleCurrentPage(1);
                }}
              />
            </div>
            <button className="btn btn-secondary" onClick={exportVehiclesReport} style={{ height: '38px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Download size={18} /> Exportar Patentes
            </button>
            <button className="btn btn-primary" onClick={() => handleOpenVehicleModal(null)}>
              <Plus size={18} /> Vincular Vehículo
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ubb-table">
            <thead>
              <tr>
                <th>Patente</th>
                <th>Propietario</th>
                <th>Observaciones</th>
                <th>Fecha Registro</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {paginatedVehicles.map((veh) => (
                <tr key={veh.patente}>
                  <td>
                    <span className="plate-badge">{veh.patente}</span>
                  </td>
                  <td style={{ fontWeight: 500 }}>{veh.propietario_nombre || 'No asignado'}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{veh.observaciones || '-'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    {format(new Date(veh.created_at), 'dd-MM-yyyy HH:mm')}
                  </td>
                  <td>
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                      onClick={() => handleOpenVehicleModal(veh)}
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
              {filteredVehicles.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No se encontraron vehículos registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Controles de paginación de vehículos */}
        {filteredVehicles.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.5rem', justifyContent: 'space-between', flexWrap: 'wrap', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Mostrando {Math.min(totalVehiclesCount, (vehicleCurrentPage - 1) * vehiclePageSize + 1)} - {Math.min(totalVehiclesCount, vehicleCurrentPage * vehiclePageSize)} de {totalVehiclesCount} vehículos
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setVehicleCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={vehicleCurrentPage === 1}
                style={{ padding: '0.5rem 1rem' }}
              >
                Anterior
              </button>
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
                Página {vehicleCurrentPage} de {totalVehiclePages}
              </div>
              <button 
                className="btn btn-secondary" 
                onClick={() => setVehicleCurrentPage(prev => Math.min(totalVehiclePages, prev + 1))}
                disabled={vehicleCurrentPage === totalVehiclePages}
                style={{ padding: '0.5rem 1rem' }}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Incidents Table */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={20} color="var(--status-warning)" /> Gestión de Incidencias
          </h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Mostrar:</span>
              <select
                className="input-field"
                style={{ width: '75px', height: '38px', padding: '0 0.5rem' }}
                value={incidentPageSize}
                onChange={(e) => {
                  setIncidentPageSize(Number(e.target.value));
                  setIncidentCurrentPage(1);
                }}
              >
                <option value={20}>20</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
              <Plus size={18} /> Registrar Incidencia
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ubb-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Patente</th>
                <th>Descripción</th>
                <th>Fecha Registro</th>
                <th>Estado</th>
                <th style={{ textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {paginatedIncidents.map((inc) => (
                <tr key={inc.id}>
                  <td style={{ color: 'var(--text-secondary)' }}>#{inc.id}</td>
                  <td>
                    {inc.vehiculo_patente ? (
                      <span className="plate-badge">{inc.vehiculo_patente}</span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>N/A</span>
                    )}
                  </td>
                  <td>{inc.descripcion}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    {format(new Date(inc.fecha_creacion), 'dd-MM-yyyy HH:mm')}
                  </td>
                  <td>
                    <span className={`badge ${inc.estado === 'cerrada' ? 'badge-success' : 'badge-danger'}`}>
                      {inc.estado === 'cerrada' ? 'Resuelto' : 'Pendiente'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={() => handleOpenEditModal(inc)}
                      >
                        Editar
                      </button>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--status-danger)' }}
                        onClick={() => handleDeleteIncident(inc.id)}
                      >
                        Borrar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {paginatedIncidents.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No hay incidencias registradas.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Controles de paginación de incidencias */}
        {totalIncidentsCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.5rem', justifyContent: 'space-between', flexWrap: 'wrap', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Mostrando {Math.min(totalIncidentsCount, (incidentCurrentPage - 1) * incidentPageSize + 1)} - {Math.min(totalIncidentsCount, incidentCurrentPage * incidentPageSize)} de {totalIncidentsCount} incidencias
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setIncidentCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={incidentCurrentPage === 1}
                style={{ padding: '0.5rem 1rem' }}
              >
                Anterior
              </button>
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
                Página {incidentCurrentPage} de {totalIncidentPages}
              </div>
              <button 
                className="btn btn-secondary" 
                onClick={() => setIncidentCurrentPage(prev => Math.min(totalIncidentPages, prev + 1))}
                disabled={incidentCurrentPage === totalIncidentPages}
                style={{ padding: '0.5rem 1rem' }}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
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

      {/* Modal para Vincular/Editar Vehículo */}
      {isVehicleModalOpen && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                {selectedVehicle ? 'Editar Vehículo' : 'Vincular Vehículo'}
              </h3>
              <button onClick={() => setIsVehicleModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSaveVehicle} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Patente *</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="Ej. CRJC39"
                  value={vehicleForm.patente}
                  onChange={(e) => setVehicleForm(prev => ({ ...prev, patente: e.target.value }))}
                  required
                  disabled={selectedVehicle !== null}
                  maxLength={10}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Propietario *</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="Nombre del propietario..."
                  value={vehicleForm.propietario_nombre}
                  onChange={(e) => setVehicleForm(prev => ({ ...prev, propietario_nombre: e.target.value }))}
                  required
                />
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Observaciones</label>
                <textarea 
                  className="input-field" 
                  rows="2"
                  placeholder="Observaciones o notas adicionales..."
                  value={vehicleForm.observaciones}
                  onChange={(e) => setVehicleForm(prev => ({ ...prev, observaciones: e.target.value }))}
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsVehicleModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submittingVehicle}>
                  {submittingVehicle ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal para Editar Incidencia */}
      {isEditModalOpen && editingIncident && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Editar Incidencia</h3>
              <button onClick={() => { setIsEditModalOpen(false); setEditingIncident(null); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSaveEditIncident} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.75rem' }}>Estado de la Incidencia *</label>
                <div style={{ display: 'flex', gap: '1.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                    <input 
                      type="radio" 
                      name="editIncidentEstado" 
                      value="abierta" 
                      checked={editingIncident.estado === 'abierta'}
                      onChange={(e) => setEditingIncident(prev => ({ ...prev, estado: e.target.value }))}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    Pendiente
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                    <input 
                      type="radio" 
                      name="editIncidentEstado" 
                      value="cerrada" 
                      checked={editingIncident.estado === 'cerrada'}
                      onChange={(e) => setEditingIncident(prev => ({ ...prev, estado: e.target.value }))}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    Resuelto
                  </label>
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Descripción de la Incidencia *</label>
                <textarea 
                  className="input-field" 
                  rows="4"
                  placeholder="Detalles de la incidencia..."
                  value={editingIncident.descripcion}
                  onChange={(e) => setEditingIncident(prev => ({ ...prev, descripcion: e.target.value }))}
                  required
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setIsEditModalOpen(false); setEditingIncident(null); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Guardar Cambios</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
