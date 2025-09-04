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
        const beforeCost = origSched.slice(0, rMonth - 1).reduce((s, x) => s + x.totalPayment, 0);
        const remBal = origSched[rMonth - 1].balance;
        const cc = remBal * (ccPct / 100);
        const remYears = Math.max(1, years - Math.floor((rMonth - 1) / 12));
        const refiSched = this.generateAmortizationSchedule(remBal, rRate, remYears);
        const afterCost = refiSched.reduce((s, x) => s + x.totalPayment, 0);
        return beforeCost + afterCost + cc;
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
            const origTotal = origSched.reduce((s, x) => s + x.totalPayment, 0);
            const initCC = hp * (ccPct / 100);
            const rTotal = this.calculateRefinanceAnalysis(principal, oR, rR, years, rM, ccPct);
            const savings = (origTotal + initCC) - rTotal;

            this.updateResults({ principal, mp, initCC, origTotal: origTotal + initCC,
                rRate: rR, rMonth: rM, rTotal, savings, dp });
            this.updateCharts(origSched, principal, oR, rR, years, rM, ccPct);
        } catch (err) {
            this.results.innerHTML = `<div style="color: #ff6b6b;"><strong>Error:</strong> ${err.message}</div>`;
        }
    }

    updateResults(data) {
        const yrs = Math.floor(data.rMonth / 12),
              mos = data.rMonth % 12,
              color = data.savings > 0 ? '#4CAF50' : '#ff6b6b',
              icon = data.savings > 0 ? '💰' : '💸',
              text = data.savings > 0 ? 'Savings' : 'Additional Cost';
        this.results.innerHTML = `
            <div style="margin-bottom:20px;">
                <h3 style="color:#4CAF50;margin-bottom:10px;">🏠 Loan Details</h3>
                <div>Principal: <strong>$${data.principal.toLocaleString()}</strong></div>
                <div>Monthly Payment: <strong>$${data.mp.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</strong></div>
                <div>Initial Closing Costs: <strong>$${data.initCC.toLocaleString()}</strong></div>
                <div>Cash at Closing: <strong>$${(data.dp + data.initCC).toLocaleString()}</strong></div>
                <div>Total Cost (30yr): <strong>$${data.origTotal.toLocaleString()}</strong></div>
            </div>
            <div>
                <h3 style="color:#2196F3;margin-bottom:10px;">🔄 Refinance Analysis</h3>
                <div>New Rate: <strong>${data.rRate}%</strong></div>
                <div>Refinance at: <strong>Month ${data.rMonth}</strong> (${yrs}y ${mos}m)</div>
                <div>Total Cost with Refi: <strong>$${data.rTotal.toLocaleString()}</strong></div>
                <div style="color:${color};font-size:1.1em;margin-top:10px;">
                    <strong>${icon} ${text}: $${Math.abs(data.savings).toLocaleString()}</strong>
                </div>
            </div>`;
    }

    updateCharts(origSched, principal, oR, rR, years, rM, ccPct) {
        this.updateBalanceChart(origSched);
        this.updatePaymentsChart(origSched);
        this.updateRefinanceChart(principal, oR, rR, years, rM, ccPct, origSched);
        this.updateSavingsChart(principal, oR, rR, years, ccPct, origSched);
    }

    updateBalanceChart(sched) {
        const ctx = this.balanceChart.getContext('2d');
        if (this.charts.balance) this.charts.balance.destroy();
        this.charts.balance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sched.map(x => x.month),
                datasets: [{
                    label: 'Loan Balance',
                    data: sched.map(x => x.balance),
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76,175,80,0.1)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#fff' } } },
                scales: {
                    x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: '#fff', callback: v => '$' + (v/1000).toFixed(0) + 'K' },
                         grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            }
        });
    }

    updatePaymentsChart(sched) {
        const ctx = this.paymentsChart.getContext('2d');
        if (this.charts.payments) this.charts.payments.destroy();
        this.charts.payments = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sched.map(x => x.month),
                datasets: [
                    {
                        label: 'Principal',
                        data: sched.map(x => x.principalPayment),
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33,150,243,0.1)',
                        fill: true,
                        tension: 0.1
                    },
                    {
                        label: 'Interest',
                        data: sched.map(x => x.interest),
                        borderColor: '#FF5722',
                        backgroundColor: 'rgba(255,87,34,0.1)',
                        fill: true,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#fff' } } },
                scales: {
                    x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            }
        });
    }

    updateRefinanceChart(principal, oRate, rRate, years, rMonth, ccPct, origSched) {
        const ctx = this.refinanceChart.getContext('2d');
        if (this.charts.refinance) this.charts.refinance.destroy();
        const monthsArr = [], costsArr = [];
        const origTotal = origSched.reduce((s,x) => s + x.totalPayment, 0);
        for (let m=1; m<=Math.min(origSched.length,240); m+=6) {
            monthsArr.push(m);
            costsArr.push(this.calculateRefinanceAnalysis(principal, oRate, rRate, years, m, ccPct));
        }
        this.charts.refinance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthsArr,
                datasets: [
                    { label:'Cost w/ Refi', data:costsArr, borderColor:'#9C27B0', fill:false, tension:0.1 },
                    { label:'Original Cost', data:monthsArr.map(()=>origTotal), borderColor:'#FF9800', borderDash:[5,5], fill:false, tension:0.1 }
                ]
            },
            options: {
                responsive:true,
                maintainAspectRatio:false,
                plugins:{ legend:{ labels:{ color:'#fff' }}},
                scales:{
                    x:{ ticks:{color:'#fff'}, grid:{color:'rgba(255,255,255,0.1)'}},
                    y:{ ticks:{color:'#fff', callback:v=>'$'+(v/1000).toFixed(0)+'K'}, grid:{color:'rgba(255,255,255,0.1)'}}
                }
            }
        });
    }

    updateSavingsChart(principal, oRate, rRate, years, ccPct, origSched) {
        const ctx = this.savingsChart.getContext('2d');
        if (this.charts.savings) this.charts.savings.destroy();
        const monthsArr = [], posArr = [], negArr = [];
        const origTotal = origSched.reduce((s,x) => s + x.totalPayment, 0);
        for (let m=1; m<=Math.min(origSched.length,240); m+=6) {
            const cost = this.calculateRefinanceAnalysis(principal, oRate, rRate, years, m, ccPct);
            const diff = origTotal - cost;
            monthsArr.push(m);
            posArr.push(diff>=0?diff:null);
            negArr.push(diff<0?diff:null);
        }
        this.charts.savings = new Chart(ctx, {
            type:'line',
            data:{
                labels:monthsArr,
                datasets:[
                    { label:'Savings', data:posArr, borderColor:'#4CAF50', backgroundColor:'rgba(76,175,80,0.2)', fill:true, spanGaps:true, tension:0.1 },
                    { label:'Additional Cost', data:negArr, borderColor:'#F44336', backgroundColor:'rgba(244,67,54,0.2)', fill:true, spanGaps:true, tension:0.1 }
                ]
            },
            options:{
                responsive:true,
                maintainAspectRatio:false,
                plugins:{ legend:{ labels:{ color:'#fff'}}},
                scales:{
                    x:{ ticks:{color:'#fff'}, grid:{color:'rgba(255,255,255,0.1)'}},
                    y:{ ticks:{color:'#fff', callback:v=>'$'+(v/1000).toFixed(0)+'K'}, grid:{color:'rgba(255,255,255,0.1)'}}
                }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new MortgageCalculator());
