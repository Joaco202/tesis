import { createClient } from '@supabase/supabase-js';

//OE acuerdate de reemplazar estas urls si NO TIENES el .env 
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://proyecto.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'anon-key';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
