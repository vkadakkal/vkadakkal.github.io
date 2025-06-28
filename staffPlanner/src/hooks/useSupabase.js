import { useState, useEffect } from 'react';
import { getSupabaseClient } from '@/lib/supabaseClient';

export const useSupabase = () => {
  const [supabase, setSupabase] = useState(null);

  useEffect(() => {
    const initSupabase = async () => {
      const client = await getSupabaseClient();
      setSupabase(client);
    };
    initSupabase();
  }, []);

  return supabase;
};
