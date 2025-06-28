'use client';

import { useState, useEffect } from 'react';
import GridStack from 'react-gridstack';
import 'react-gridstack/dist/react-gridstack.css';
import { use404Supabase } from '@/hooks/useSupabase';

export default function DemandTab() {
  const supabase = useSupabase();
  const [projects, setProjects] = useState([]);
  const [demand, setDemand] = useState([]);

  useEffect(() => {
    if (!supabase) return;
    const fetchData = async () => {
      const { data: projData } = await supabase
        .from('projects')
        .select('*');
      const { data: demandData } = await supabase
        .from('demand')
        .select('*');
      setProjects(projData || []);
      setDemand(demandData || []);
    };
    fetchData();
  }, [supabase]);

  const updateScaling = async (projectId, scalingFactor) => {
    if (!supabase) return;
    await supabase
      .from('projects')
      .update({ scaling_factor: parseFloat(scalingFactor) })
      .eq('id', projectId);
    setProjects(prev => 
      prev.map(p => 
        p.id === projectId 
          ? { ...p, scaling_factor: parseFloat(scalingFactor) } 
          : p
      )
    );
  };

  const updateDemand = async (projectId, month, fte) => {
    if (!supabase) return;
    await supabase
      .from('demand')
      .upsert(
        { project_id: projectId, month, fte: parseFloat(fte) },
        { onConflict: 'project_id,month' }
      );
    setDemand(prev => 
      prev.map(d => 
        d.project_id === projectId && d.month === month 
          ? { ...d, fte: parseFloat(fte) } 
          : d
      )
    );
  };

  return (
    <div>
      {projects.map(project => (
        <div key={project.id} className="card mb-4">
          <h3 className="text-lg font-semibold mb-3">
            {project.name} (Scaling: 
            <input 
              type="number" 
              value={project.scaling_factor} 
              onChange={(e) => updateScaling(project.id, e.target.value)}
              className="input-dark ml-2 w-16"
            />)
          </h3>
          <GridStack cellHeight={50}>
            {demand.filter(d => d.project_id === project.id).map(d => (
              <div key={`${project.id}-${d.month}`} className="grid-stack-item" gs-w={3} gs-h={1}>
                <div className="flex items-center">
                  <span className="mr-2">{d.month}:</span>
                  <input
                    type="number"
                    value={d.fte}
                    onChange={(e) => updateDemand(project.id, d.month, e.target.value)}
                    className="input-dark w-full"
                  />
                </div>
              </div>
            ))}
          </GridStack>
        </div>
      ))}
    </div>
  );
}
