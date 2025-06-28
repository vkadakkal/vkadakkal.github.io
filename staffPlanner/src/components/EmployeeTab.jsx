'use client';

import { useState, useEffect } from 'react';
import GridStack from 'react-gridstack';
import 'react-gridstack/dist/react-gridstack.css';
import { useSupabase } from '@/hooks/useSupabase';

export default function EmployeeTab() {
  const supabase = useSupabase();
  const [employees, setEmployees] = useState([]);
  const [availability, setAvailability] = useState([]);

  useEffect(() => {
    if (!supabase) return;
    const fetchData = async () => {
      const { data: empData } = await supabase
        .from('employees')
        .select('id, name, domain, manager:manager_id (name)');
      const { data: availData } = await supabase
        .from('availability')
        .select('*');
      setEmployees(empData || []);
      setAvailability(availData || []);
    };
    fetchData();
  }, [supabase]);

  const updateAvailability = async (employeeId, month, fraction) => {
    if (!supabase) return;
    await supabase
      .from('availability')
      .upsert(
        { employee_id: employeeId, month, fraction: parseFloat(fraction) },
        { onConflict: 'employee_id,month' }
      );
    setAvailability(prev => 
      prev.map(a => 
        a.employee_id === employeeId && a.month === month 
          ? { ...a, fraction: parseFloat(fraction) } 
          : a
      )
    );
  };

  return (
    <GridStack
      className="grid-stack"
      cellHeight={60}
      draggable={{ handle: '.grid-handle' }}
    >
      {employees.map(emp => (
        <div 
          key={emp.id} 
          className="grid-stack-item"
          gs-w={12} 
          gs-h={1}
        >
          <div className="card">
            <div className="grid-handle">
              {emp.name} ({emp.domain}) - {emp.manager?.name || 'No manager'}
            </div>
            <div className="grid grid-cols-12 gap-2 mt-3">
              {availability.filter(a => a.employee_id === emp.id).map(avail => (
                <input
                  key={`${emp.id}-${avail.month}`}
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={avail.fraction}
                  onChange={(e) => updateAvailability(emp.id, avail.month, e.target.value)}
                  className="input-dark text-center"
                />
              ))}
            </div>
          </div>
        </div>
      ))}
    </GridStack>
  );
}
