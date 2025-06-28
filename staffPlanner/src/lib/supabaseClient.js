import { createClient } from '@supabase/supabase-js';

let supabase = null;

export const getSupabaseClient = async () => {
  if (supabase) return supabase;
  
  const response = await fetch('/config.json');
  const config = await response.json();
  
  supabase = createClient(config.SUPABASE_URL, config.SUPABASE_KEY);
  return supabase;
};
