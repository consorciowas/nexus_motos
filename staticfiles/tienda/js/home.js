Chart.register(ChartDataLabels);

const fmtSoles = (v)=> (Number(v||0)).toLocaleString('es-PE', {minimumFractionDigits:2, maximumFractionDigits:2});
const textColor = '#474849';
const gridColor = 'rgba(148,163,184,.2)';
const borderColor = 'rgba(99,102,241,.35)';

const palette = {
  azul:   'rgba(37, 99, 235, 0.7)', //'#2563eb'
  verde:  '#10b981',
  ambar:  '#f59e0b',
  rojo:   '#ef4444',
  indigo: 'rgba(99, 102, 241,0.7)', //'#6366f1', 
  cyan:   '#06b6d4',
  pink:   'rgba(236, 72, 153, 0.7)', //'#ec4899'
};

let charts = {}; // refs

async function fetchJSON(url){
  const r = await fetch(url, {headers: {'X-Requested-With':'XMLHttpRequest'}});
  if(!r.ok){ const t = await r.text(); throw new Error(t || r.statusText); }
  return await r.json();
}

function destroy(id){ if(charts[id]){ charts[id].destroy(); charts[id]=null; } }

const actInicial = document.getElementById('actInicial');
// ---------- Carga inicial (sección 2 & estado) ----------
(async function initOverview(){
  actInicial.innerHTML = `
        <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
        Actualizando...
  `;
  try{
    const data = await fetchJSON("/api/dashboard/overview/");
    fillResumenTable(data);
    drawBarTotales6M(data);
    drawStackedTipos6M(data);
    drawLineUtilidad6M(data);
    drawStackedCanal6M(data);
    drawBarTopTipo6M(data);

    const state = await fetchJSON("/api/dashboard/state/");
    fillEstadoTable(state);
    drawDonaEstado(state);
  }catch(err){ 
    console.error(err); alert("Error cargando overview: " + err.message); 
  }finally{
    actInicial.innerHTML = 'Actualizado';
  }
})();

function fillResumenTable(data){
  const tb = document.querySelector("#tablaResumen6M tbody");
  tb.innerHTML = "";
  data.resumen.forEach(r=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.mes}</td>
      <td>${r.efectivo_n}</td><td>${fmtSoles(r.efectivo_total)}</td>
      <td>${r.credito_n}</td><td>${fmtSoles(r.credito_total)}</td>
      <td>${r.mixto_n}</td><td>${fmtSoles(r.mixto_total)}</td>
      <td>${fmtSoles(r.total_mes)}</td>
    `;
    tb.appendChild(tr);
  });
}

function drawBarTotales6M(d){
  destroy('barTotales6M');
  charts.barTotales6M = new Chart(document.getElementById('barTotales6M'), {
    type:'bar',
    data:{
      labels:d.labels_6m,
      datasets:[{
        label:'Total ventas (S/)',
        data:d.barras_totales,
        backgroundColor: palette.indigo,
        borderColor: borderColor,
        //borderWidth:1.5,
        //borderRadius:8
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{labels:{color:textColor}},
        datalabels:{ color:'#000', anchor:'end', align:'end', formatter:(v)=>'S/ '+fmtSoles(v), clamp:true }
      },
      scales:{
        x:{ ticks:{color:textColor}, grid:{color:gridColor} },
        y:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true }
      }
    }
  });
}

function drawStackedTipos6M(d){
  destroy('stackedTipos6M');
  charts.stackedTipos6M = new Chart(document.getElementById('stackedTipos6M'), {
    type:'bar',
    data:{
      labels:d.labels_6m,
      datasets:[
        {label:'Efectivo', data:d.stacked_por_tipo.EFECTIVO, backgroundColor:palette.verde/*, borderRadius:6*/},
        {label:'Crédito',  data:d.stacked_por_tipo.CREDITO,  backgroundColor:palette.ambar/*, borderRadius:6*/},
        {label:'Mixto',    data:d.stacked_por_tipo.MIXTO,    backgroundColor:palette.rojo/*,  borderRadius:6*/},
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{ legend:{labels:{color:textColor}}, datalabels:{display:false} },
      scales:{
        x:{ stacked:true, ticks:{color:textColor}, grid:{color:gridColor} },
        y:{ stacked:true, ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true }
      }
    }
  });
}

function drawLineUtilidad6M(d){
  destroy('lineUtilidad6M');
  charts.lineUtilidad6M = new Chart(document.getElementById('lineUtilidad6M'), {
    type:'line',
    data:{
      labels:d.labels_6m,
      datasets:[{
        label:'Utilidad (S/)',
        data:d.utilidades,
        tension:.35,
        fill:false,
        borderWidth:2.5,
        borderColor: palette.cyan,
        pointBackgroundColor: '#0ea5e9',
        pointRadius:4
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{ legend:{labels:{color:textColor}}, datalabels:{display:false} },
      scales:{
        x:{ ticks:{color:textColor}, grid:{color:gridColor} },
        y:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true }
      }
    }
  });
}

function drawStackedCanal6M(d){
  destroy('stackedCanal6M');
  charts.stackedCanal6M = new Chart(document.getElementById('stackedCanal6M'), {
    type:'bar',
    data:{
      labels:d.labels_6m,
      datasets:[
        {label:'Tienda', data:d.ventas_canal_tienda, backgroundColor:palette.azul/*, borderRadius:6*/},
        {label:'Online', data:d.ventas_canal_online, backgroundColor:palette.pink/*, borderRadius:6*/},
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{ legend:{labels:{color:textColor}}, datalabels:{display:false} },
      scales:{
        x:{ stacked:true, ticks:{color:textColor}, grid:{color:gridColor} },
        y:{ stacked:true, ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true }
      }
    }
  });
}

function drawBarTopTipo6M(d){
  destroy('barTopTipo6M');
  charts.barTopTipo6M = new Chart(document.getElementById('barTopTipo6M'), {
    type:'bar',
    data:{
      labels:d.labels_6m,
      datasets:[
        {label:'MOTO', data:d.top_mes_moto, backgroundColor:palette.ambar/*, borderRadius:6*/},
        {label:'ACCESORIO', data:d.top_mes_accesorio, backgroundColor:palette.verde/*, borderRadius:6*/},
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{ 
        legend:{labels:{color:textColor}}, 
        datalabels:{ color:'#000', anchor:'end', align:'end' }, 
        tooltip:{
          callbacks:{
            label: function(context){
              let value = context.raw;
              let idx = context.dataIndex;

              if(context.dataset.label === "MOTO"){
                return `${context.dataset.label}: ${value} (${d.nombre_mes_moto[idx]})`;
              } else {
                return `${context.dataset.label}: ${value} (${d.nombre_mes_accesorio[idx]})`;
              }
            }
          }
        }
      },
      scales:{
        x:{ ticks:{color:textColor}, grid:{color:gridColor} },
        y:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true, precision:0 }
      }
    }
  });
}

function fillEstadoTable(state){
  const tb = document.querySelector("#tablaEstado tbody");
  tb.innerHTML = "";
  state.detalle.forEach(it=>{
    const badge = it.estado === 'ok' ? 'text-emerald-300' : it.estado === 'por_agotar' ? 'text-amber-300' : 'text-red-300';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${it.nombre}</td>
      <td>${it.stock}</td>
      <td>${it.minimo}</td>
      <td class="${badge} uppercase font-semibold">${it.estado}</td>
    `;
    tb.appendChild(tr);
  });
  const r = document.getElementById('resumenEstado');
  r.innerHTML = `Total: <b>${state.total}</b> · Agotado: <b class="text-red-300">${state.counts.agotado}</b> (${state.percentages.agotado}%)
   · Por agotar: <b class="text-amber-300">${state.counts.por_agotar}</b> (${state.percentages.por_agotar}%)
   · OK: <b class="text-emerald-300">${state.counts.ok}</b> (${state.percentages.ok}%)`;
}

function drawDonaEstado(state){
  destroy('donaEstado');
  charts.donaEstado = new Chart(document.getElementById('donaEstado'), {
    type:'doughnut',
    data:{
      labels:['Agotado','Por agotar','OK'],
      datasets:[{
        data:[state.percentages.agotado, state.percentages.por_agotar, state.percentages.ok],
        backgroundColor:[palette.rojo, palette.ambar, palette.verde],
        borderWidth:1.5,
        cutout:'55%'
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio: true,
      aspectRatio: 1,   // mantiene forma cuadrada
      radius: "90%",    // evita que se salga del canvas
      plugins:{
        legend:{labels:{color:textColor}},
        datalabels:{
          color:'#111827',
          formatter:(v)=> v+'%',
          backgroundColor:'#e5e7eb',
          borderRadius:6,
          padding:4,
          clamp:true
        }
      }
    }
  });
}

// ---------- Filtro (Sección 3) ----------
const btnAplicar = document.getElementById('btnAplicar');
btnAplicar.addEventListener('click', async ()=>{
  const s = document.getElementById('fStart').value;
  const e = document.getElementById('fEnd').value;
  if(!s || !e) return alert('Seleccione ambas fechas.');
  if(e < s) return alert('La fecha fin no puede ser menor que la fecha inicio.');

  const spinner = document.getElementById('spinner');
  spinner.classList.remove("d-none");
  btnAplicar.disabled = true;
  try{
    const url = new URL("/api/dashboard/filter/", window.location.origin);
    url.searchParams.set('start', s);
    url.searchParams.set('end', e);
    const data = await fetchJSON(url);

    // KPIs
    document.getElementById('kpiCompras').innerText = fmtSoles(data.kpis.compras);
    document.getElementById('kpiVentas').innerText = fmtSoles(data.kpis.ventas);
    document.getElementById('kpiUtilidad').innerText = fmtSoles(data.kpis.utilidad);

    // Top 8 (horizontal)
    destroy('barTop8');
    charts.barTop8 = new Chart(document.getElementById('barTop8'), {
      type:'bar',
      data:{
        labels:data.top8.labels,
        datasets:[{ label:'Cantidad vendida', data:data.top8.values, backgroundColor:palette.indigo/*, borderRadius:6*/ }]
      },
      options:{
        indexAxis:'y',
        responsive:true,
        plugins:{ legend:{labels:{color:textColor}}, datalabels:{ color:'#000', anchor:'end', align:'right' } },
        scales:{
          x:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true, precision:0 },
          y:{ ticks:{color:textColor}, grid:{color:gridColor} }
        }
      }
    });

    // Áreas apiladas (usaremos área simple)
    destroy('areaDiaria');
    charts.areaDiaria = new Chart(document.getElementById('areaDiaria'), {
      type:'line',
      data:{
        labels:data.diarios.labels,
        datasets:[{ label:'Ventas diarias (S/)', data:data.diarios.values, fill:true, tension:.35, borderColor:palette.verde, backgroundColor:'rgba(16,185,129,.25)' }]
      },
      options:{
        responsive:true,
        plugins:{ legend:{labels:{color:textColor}}, datalabels:{display:false} },
        scales:{
          x:{ ticks:{color:textColor}, grid:{color:gridColor} },
          y:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true }
        }
      }
    });

    // Top 5 vendedores (horizontal)
    destroy('barVendedores');
    charts.barVendedores = new Chart(document.getElementById('barVendedores'), {
      type:'bar',
      data:{
        labels:data.top_vendedores.labels,
        datasets:[{ label:'# Ventas', data:data.top_vendedores.values, backgroundColor:palette.ambar/*, borderRadius:6*/ }]
      },
      options:{
        indexAxis:'y',
        responsive:true,
        plugins:{ legend:{labels:{color:textColor}}, datalabels:{ color:'#000', anchor:'end', align:'right' } },
        scales:{
          x:{ ticks:{color:textColor}, grid:{color:gridColor}, beginAtZero:true, precision:0 },
          y:{ ticks:{color:textColor}, grid:{color:gridColor} }
        }
      }
    });

    // Pie “3D-like” por tipo
    destroy('pieTipo');
    charts.pieTipo = new Chart(document.getElementById('pieTipo'), {
      type:'pie',
      data:{
        labels:data.por_tipo.labels,
        datasets:[{ data:data.por_tipo.values, backgroundColor:[palette.ambar, palette.verde], borderWidth:1.5 }]
      },
      options:{
        responsive:true,
        plugins:{
          legend:{labels:{color:textColor}},
          datalabels:{ color:'#fff', formatter:(v,ctx)=>{
            const total = ctx.dataset.data.reduce((a,b)=>a+b,0)||1;
            const pct = Math.round(v*100/total);
            return `${v} (${pct}%)`;
          }}
        }
      }
    });

    // Donut por canal
    destroy('donaCanal');
    charts.donaCanal = new Chart(document.getElementById('donaCanal'), {
      type:'doughnut',
      data:{
        labels:data.canal.labels,
        datasets:[{ data:data.canal.values, backgroundColor:[palette.azul, palette.pink], cutout:'55%' }]
      },
      options:{
        responsive:true,
        plugins:{ legend:{labels:{color:textColor}}, datalabels:{ color:'#fff' } }
      }
    });

    // Half donut entregas online
    document.getElementById('totalOnline').innerText = data.online_entrega.total_online;
    destroy('halfDonaOnline');
    charts.halfDonaOnline = new Chart(document.getElementById('halfDonaOnline'), {
      type:'doughnut',
      data:{
        labels:data.online_entrega.labels,
        datasets:[{ data:data.online_entrega.values, backgroundColor:[palette.verde, palette.rojo], circumference:180, rotation:270, cutout:'60%' }]
      },
      options:{
        responsive:true,
        plugins:{ legend:{labels:{color:textColor}}, datalabels:{ color:'#fff' } }
      }
    });

  }catch(err){ 
    console.error(err); alert("Error al aplicar filtro: " + err.message); 
  }finally{
    spinner.classList.add("d-none");
    btnAplicar.disabled = false;
  }
});

// Cargar gráficos de la sección 3 al inicio con el rango por defecto
btnAplicar.click();