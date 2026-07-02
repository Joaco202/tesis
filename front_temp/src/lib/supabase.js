import { createClient } from '@supabase/supabase-js';

// Reemplazar estas URLs por las variables de entorno en producción o el .env local
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://tu-proyecto.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'tu-anon-key';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
