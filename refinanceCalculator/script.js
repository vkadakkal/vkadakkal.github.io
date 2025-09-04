class MortgageCalculator {
    constructor() {
        this.charts = {};
        this.initializeElements();
        this.setupEventListeners();
        this.calculate();
    }

    initializeElements() {
        this.homePrice = document.getElementById('homePrice');
        this.downPayment = document.getElementById('downPayment');
        this.originalRate = document.getElementById('originalRate');
        this.closingCosts = document.getElementById('closingCosts');
        this.refinanceRate = document.getElementById('refinanceRate');
        this.refinanceMonth = document.getElementById('refinanceMonth');
        this.refinanceRateValue = document.getElementById('refinanceRateValue');
        this.refinanceMonthValue = document.getElementById('refinanceMonthValue');
        this.results = document.getElementById('results');
        this.balanceChart = document.getElementById('balanceChart');
        this.paymentsChart = document.getElementById('paymentsChart');
        this.refinanceChart = document.getElementById('refinanceChart');
        this.savingsChart = document.getElementById('savingsChart');
    }

    setupEventListeners() {
        [this.homePrice, this.downPayment, this.originalRate, this.closingCosts]
            .forEach(input => input.addEventListener('input', () => this.calculate()));

        this.refinanceRate.addEventListener('input', e => {
            this.refinanceRateValue.textContent = `${e.target.value}%`;
            this.calculate();
        });

        this.refinanceMonth.addEventListener('input', e => {
            const months = parseInt(e.target.value);
            const years = Math.floor(months / 12);
            const rem = months % 12;
            this.refinanceMonthValue.textContent = `${months} (${years}y ${rem}m)`;
            this.calculate();
        });

        document.getElementById('calculateBtn')
            .addEventListener('click', () => this.calculate());
    }

    monthlyPayment(principal, rate, years) {
        const r = rate / 100 / 12, n = years * 12;
        if (r === 0) return principal / n;
        return principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    }

    generateAmortizationSchedule(principal, rate, years) {
        const mp = this.monthlyPayment(principal, rate, years);
        let bal = principal, sched = [];
        for (let m = 1; m <= years * 12; m++) {
            const interest = bal * (rate / 100 / 12);
            const pmt = mp - interest;
            bal = Math.max(0, bal - pmt);
            sched.push({ month: m, principalPayment: pmt, interest, balance: bal, totalPayment: pmt + interest });
            if (bal <= 0) break;
        }
        return sched;
    }

    calculateRefinanceAnalysis(principal, oRate, rRate, years, rMonth, ccPct) {
        const origSched = this.generateAmortizationSchedule(principal, oRate, years);
        if (rMonth > origSched.length) return Infinity;

        const beforeCost = origSched.slice(0, rMonth - 1)
            .reduce((sum, x) => sum + x.totalPayment, 0);
        const remBal = origSched[rMonth - 1].balance;
        const refiClosingCosts = remBal * (ccPct / 100);
        const remMonths = years * 12 - (rMonth - 1);
        const remYears = Math.max(1, remMonths / 12);
        const refiSched = this.generateAmortizationSchedule(remBal, rRate, remYears);
        const afterCost = refiSched.reduce((sum, x) => sum + x.totalPayment, 0);

        return beforeCost + afterCost + refiClosingCosts;
    }

    calculate() {
        try {
            const hp = parseFloat(this.homePrice.value);
            const dp = parseFloat(this.downPayment.value);
            const oR = parseFloat(this.originalRate.value);
            const ccPct = parseFloat(this.closingCosts.value);
            const rR = parseFloat(this.refinanceRate.value);
            const rM = parseInt(this.refinanceMonth.value);

            const principal = hp - dp, years = 30;
            const origSched = this.generateAmortizationSchedule(principal, oR, years);
            const mp = this.monthlyPayment(principal, oR, years);
            const origLoanTotal = origSched.reduce((s, x) => s + x.totalPayment, 0);
            const initCC = hp * (ccPct / 100);
            
            // UPDATED: Include initial closing costs in original total
            const origTotalWithClosing = origLoanTotal + initCC;
            
            const rTotal = this.calculateRefinanceAnalysis(principal, oR, rR, years, rM, ccPct);
            
            // UPDATED: Compare totals including closing costs
            const savings = origTotalWithClosing - rTotal;

            this.updateResults({
                principal, mp, initCC,
                origLoanTotal: origLoanTotal,
                origTotalWithClosing: origTotalWithClosing,
                rRate: rR, rMonth: rM, rTotal, savings, dp
            });
            this.updateCharts(origSched, principal, oR, rR, years, rM, ccPct, initCC);
        } catch (err) {
            this.results.innerHTML = `<div style="color:#ff6b6b;"><strong>Error:</strong> ${err.message}</div>`;
        }
    }

    updateResults(data) {
        const yrs = Math.floor(data.rMonth / 12),
              mos = data.rMonth % 12,
              clr = data.savings > 0 ? '#4CAF50' : '#F44336',
              bgClr = data.savings > 0 ? 'rgba(76,175,80,0.1)' : 'rgba(244,67,54,0.1)',
              icon = data.savings > 0 ? '💰' : '❌',
              txt = data.savings > 0 ? 'Total Savings' : 'Total Loss';

        this.results.innerHTML = `
            <div style="margin-bottom:20px;">
                <h3 style="color:#4CAF50;margin-bottom:10px;">🏠 Original Loan</h3>
                <div>Principal: <strong>$${data.principal.toLocaleString()}</strong></div>
                <div>Monthly Payment: <strong>$${data.mp.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</strong></div>
                <div>Loan Payments (30yr): <strong>$${data.origLoanTotal.toLocaleString()}</strong></div>
                <div>Initial Closing Costs: <strong>$${data.initCC.toLocaleString()}</strong></div>
                <div style="border-top:1px solid #555;padding-top:8px;margin-top:8px;">
                    <strong>Total Cost: $${data.origTotalWithClosing.toLocaleString()}</strong>
                </div>
                <div>Cash at Closing: <strong>$${(data.dp+data.initCC).toLocaleString()}</strong></div>
            </div>
            <div>
                <h3 style="color:#2196F3;margin-bottom:10px;">🔄 Refinance Scenario</h3>
                <div>New Rate: <strong>${data.rRate}%</strong></div>
                <div>Refinance at: <strong>Month ${data.rMonth}</strong> (${yrs}y ${mos}m)</div>
                <div>Total Cost with Refi: <strong>$${data.rTotal.toLocaleString()}</strong></div>
                <div style="color:${clr};background:${bgClr};padding:10px;border-radius:8px;margin-top:10px;border-left:4px solid ${clr};">
                    <strong style="font-size:1.1em;">${icon} ${txt}: $${Math.abs(data.savings).toLocaleString()}</strong>
                    ${data.savings < 0 ? '<div style="font-size:0.9em;margin-top:5px;">⚠️ Refinancing would cost more</div>' : ''}
                </div>
            </div>`;
    }

    updateCharts(origSched, principal, oR, rR, years, rM, ccPct, initCC) {
        this.updateBalanceChart(origSched);
        this.updatePaymentsChart(origSched);
        this.updateRefinanceChart(principal, oR, rR, years, rM, ccPct, origSched, initCC);
        this.updateSavingsChart(principal, oR, rR, years, ccPct, origSched, initCC);
    }

    updateBalanceChart(sched) {
        const ctx = this.balanceChart.getContext('2d');
        if (this.charts.balance) this.charts.balance.destroy();
        this.charts.balance = new Chart(ctx, {
            type:'line',
            data:{ labels:sched.map(x=>x.month), datasets:[{
                label:'Loan Balance', data:sched.map(x=>x.balance),
                borderColor:'#4CAF50', backgroundColor:'rgba(76,175,80,0.1)', fill:true, tension:0.1
            }]},
            options:{ responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{ labels:{ color:'#fff' }}},
                scales:{ x:{ ticks:{ color:'#fff' }, grid:{ color:'rgba(255,255,255,0.1)'}},
                         y:{ ticks:{ color:'#fff', callback:v=>`$${(v/1000).toFixed(0)}K` }, grid:{ color:'rgba(255,255,255,0.1)'}}}
            }
        });
    }

    updatePaymentsChart(sched) {
        const ctx = this.paymentsChart.getContext('2d');
        if (this.charts.payments) this.charts.payments.destroy();
        this.charts.payments = new Chart(ctx, {
            type:'line',
            data:{ labels:sched.map(x=>x.month), datasets:[
                { label:'Principal', data:sched.map(x=>x.principalPayment),
                  borderColor:'#2196F3', backgroundColor:'rgba(33,150,243,0.1)', fill:true, tension:0.1 },
                { label:'Interest', data:sched.map(x=>x.interest),
                  borderColor:'#FF5722', backgroundColor:'rgba(255,87,34,0.1)', fill:true, tension:0.1 }
            ]},
            options:{ responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{ labels:{ color:'#fff' }}},
                scales:{ x:{ ticks:{ color:'#fff' }, grid:{ color:'rgba(255,255,255,0.1)'}},
                         y:{ ticks:{ color:'#fff' }, grid:{ color:'rgba(255,255,255,0.1)'}}}
            }
        });
    }

    updateRefinanceChart(principal, oR, rR, years, rM, ccPct, origSched, initCC) {
        const ctx = this.refinanceChart.getContext('2d');
        if (this.charts.refinance) this.charts.refinance.destroy();
        const monthsArr=[], costsArr=[];
        
        // UPDATED: Include initial closing costs in original total
        const origTotalWithClosing = origSched.reduce((s,x)=>s+x.totalPayment,0) + initCC;
        
        for(let m=1; m<=Math.min(origSched.length,240); m+=3){
            monthsArr.push(m);
            costsArr.push(this.calculateRefinanceAnalysis(principal, oR, rR, years, m, ccPct));
        }
        const currentCost = this.calculateRefinanceAnalysis(principal, oR, rR, years, rM, ccPct);
        
        this.charts.refinance = new Chart(ctx,{
            type:'line',
            data:{
                labels:monthsArr,
                datasets:[
                    { label:'Total Cost w/ Refi', data:costsArr,
                      borderColor:'#9C27B0', backgroundColor:'rgba(156,39,176,0.1)',
                      fill:false, tension:0.4, pointRadius:1, pointHoverRadius:4 },
                    { label:'Original Total Cost', data:monthsArr.map(()=>origTotalWithClosing),
                      borderColor:'#FF9800', borderDash:[5,5], fill:false, pointRadius:0 },
                    { label:'Current Selection', data:monthsArr.map(m=>m===rM?currentCost:null),
                      borderColor: currentCost < origTotalWithClosing ? '#4CAF50' : '#F44336',
                      backgroundColor: currentCost < origTotalWithClosing ? '#4CAF50' : '#F44336',
                      showLine:false, fill:false, pointRadius:6, pointHoverRadius:8 }
                ]
            },
            options:{
                responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{ labels:{ color:'#fff' }}},
                scales:{
                    x:{ title:{ display:true, text:'Refinance Month', color:'#fff'},
                        ticks:{ color:'#fff' }, grid:{ color:'rgba(255,255,255,0.1)'}},
                    y:{ title:{ display:true, text:'Total Cost ($)', color:'#fff'},
                        ticks:{ color:'#fff', callback:v=>`$${(v/1000).toFixed(0)}K` },
                        grid:{ color:'rgba(255,255,255,0.1)'} }
                }
            }
        });
    }

    updateSavingsChart(principal, oR, rR, years, ccPct, origSched, initCC) {
        const ctx = this.savingsChart.getContext('2d');
        if (this.charts.savings) this.charts.savings.destroy();
        const monthsArr=[], posArr=[], negArr=[];
        
        // UPDATED: Include initial closing costs in original total
        const origTotalWithClosing = origSched.reduce((s,x)=>s+x.totalPayment,0) + initCC;
        
        for(let m=1; m<=Math.min(origSched.length,240); m+=3){
            const cost = this.calculateRefinanceAnalysis(principal, oR, rR, years, m, ccPct);
            const diff = origTotalWithClosing - cost;
            monthsArr.push(m);
            posArr.push(diff>=0?diff:null);
            negArr.push(diff<0?Math.abs(diff):null); // Show absolute value for losses
        }
        
        this.charts.savings = new Chart(ctx,{
            type:'line',
            data:{
                labels:monthsArr,
                datasets:[
                    { label:'💰 Savings', data:posArr,
                      borderColor:'#4CAF50', backgroundColor:'rgba(76,175,80,0.3)',
                      fill:true, spanGaps:true, tension:0.1 },
                    { label:'❌ Additional Cost', data:negArr,
                      borderColor:'#F44336', backgroundColor:'rgba(244,67,54,0.3)',
                      fill:true, spanGaps:true, tension:0.1 }
                ]
            },
            options:{
                responsive:true, maintainAspectRatio:false,
                plugins:{ 
                    legend:{ labels:{ color:'#fff' }},
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                if (value === null) return '';
                                const isLoss = context.dataset.label.includes('❌');
                                return `${context.dataset.label}: $${value.toLocaleString()}${isLoss ? ' loss' : ' savings'}`;
                            }
                        }
                    }
                },
                scales:{
                    x:{ title:{ display:true, text:'Refinance Month', color:'#fff'},
                        ticks:{ color:'#fff' }, grid:{ color:'rgba(255,255,255,0.1)'}},
                    y:{ title:{ display:true, text:'Amount ($)', color:'#fff'},
                        ticks:{ color:'#fff', callback:v=>`$${(v/1000).toFixed(0)}K` },
                        grid:{ color:'rgba(255,255,255,0.1)'} }
                }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new MortgageCalculator());
