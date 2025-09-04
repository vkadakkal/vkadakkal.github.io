class MortgageCalculator {
    constructor() {
        this.charts = {};
        this.initializeElements();
        this.setupEventListeners();
        this.calculate();
    }

    initializeElements() {
        // Input elements
        this.homePrice = document.getElementById('homePrice');
        this.downPayment = document.getElementById('downPayment');
        this.originalRate = document.getElementById('originalRate');
        this.closingCosts = document.getElementById('closingCosts');
        this.refinanceRate = document.getElementById('refinanceRate');
        this.refinanceMonth = document.getElementById('refinanceMonth');
        
        // Display elements
        this.refinanceRateValue = document.getElementById('refinanceRateValue');
        this.refinanceMonthValue = document.getElementById('refinanceMonthValue');
        this.results = document.getElementById('results');
        
        // Chart elements
        this.balanceChart = document.getElementById('balanceChart');
        this.paymentsChart = document.getElementById('paymentsChart');
        this.refinanceChart = document.getElementById('refinanceChart');
        this.savingsChart = document.getElementById('savingsChart');
    }

    setupEventListeners() {
        // Input change listeners
        [this.homePrice, this.downPayment, this.originalRate, this.closingCosts].forEach(input => {
            input.addEventListener('input', () => this.calculate());
        });

        // Slider listeners
        this.refinanceRate.addEventListener('input', (e) => {
            this.refinanceRateValue.textContent = `${e.target.value}%`;
            this.calculate();
        });

        this.refinanceMonth.addEventListener('input', (e) => {
            const months = parseInt(e.target.value);
            const years = Math.floor(months / 12);
            const remainingMonths = months % 12;
            this.refinanceMonthValue.textContent = `${months} (${years}y ${remainingMonths}m)`;
            this.calculate();
        });

        // Calculate button
        document.getElementById('calculateBtn').addEventListener('click', () => this.calculate());

        // Tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchChart(e.target.dataset.chart);
            });
        });
    }

    monthlyPayment(principal, annualRate, years) {
        const r = annualRate / 100 / 12;
        const n = years * 12;
        if (r === 0) return principal / n;
        return principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    }

    generateAmortizationSchedule(principal, annualRate, years) {
        const monthlyPmt = this.monthlyPayment(principal, annualRate, years);
        let balance = principal;
        const schedule = [];

        for (let month = 1; month <= years * 12; month++) {
            const interest = balance * (annualRate / 100 / 12);
            const principalPayment = monthlyPmt - interest;
            balance = Math.max(0, balance - principalPayment);
            
            schedule.push({
                month,
                principalPayment,
                interest,
                balance,
                totalPayment: principalPayment + interest
            });

            if (balance <= 0) break;
        }

        return schedule;
    }

    calculateRefinanceAnalysis(principal, origRate, refiRate, years, refiMonth, closingCostsPct) {
        const origSchedule = this.generateAmortizationSchedule(principal, origRate, years);
        if (refiMonth > origSchedule.length) return Infinity;

        // Cost before refinance
        const costBefore = origSchedule
            .slice(0, refiMonth - 1)
            .reduce((sum, p) => sum + p.totalPayment, 0);

        // Remaining balance & closing costs
        const remainingBalance = origSchedule[refiMonth - 1].balance;
        const closingCosts = remainingBalance * (closingCostsPct / 100);

        // New schedule after refinance
        const remainingYears = Math.max(1, years - Math.floor((refiMonth - 1) / 12));
        const refiSchedule = this.generateAmortizationSchedule(remainingBalance, refiRate, remainingYears);
        const costAfter = refiSchedule.reduce((sum, p) => sum + p.totalPayment, 0);

        return costBefore + costAfter + closingCosts;
    }

    calculate() {
        try {
            // Get input values
            const homePrice = parseFloat(this.homePrice.value);
            const downPayment = parseFloat(this.downPayment.value);
            const origRate = parseFloat(this.originalRate.value);
            const closingCostsPct = parseFloat(this.closingCosts.value);
            const refiRate = parseFloat(this.refinanceRate.value);
            const refiMonth = parseInt(this.refinanceMonth.value);

            // Calculate loan details
            const principal = homePrice - downPayment;
            const years = 30;
            
            // Original loan calculations
            const origSchedule = this.generateAmortizationSchedule(principal, origRate, years);
            const monthlyPmt = this.monthlyPayment(principal, origRate, years);
            const origTotal = origSchedule.reduce((sum, p) => sum + p.totalPayment, 0);
            const initialClosingCosts = homePrice * (closingCostsPct / 100);

            // Refinance analysis
            const refiTotal = this.calculateRefinanceAnalysis(
                principal, origRate, refiRate, years, refiMonth, closingCostsPct
            );
            const savings = (origTotal + initialClosingCosts) - refiTotal;

            // Update results display
            this.updateResults({
                principal,
                monthlyPmt,
                initialClosingCosts,
                origTotal: origTotal + initialClosingCosts,
                refiRate,
                refiMonth,
                refiTotal,
                savings,
                downPayment
            });

            // Update charts
            this.updateCharts(origSchedule, principal, origRate, refiRate, years, refiMonth, closingCostsPct);

        } catch (error) {
            this.results.innerHTML = `<div style="color: #ff6b6b;"><strong>Error:</strong> ${error.message}</div>`;
        }
    }

    updateResults(data) {
        const years = Math.floor(data.refiMonth / 12);
        const months = data.refiMonth % 12;
        const savingsColor = data.savings > 0 ? '#4CAF50' : '#ff6b6b';
        const savingsIcon = data.savings > 0 ? '💰' : '💸';
        const savingsText = data.savings > 0 ? 'Savings' : 'Additional Cost';

        this.results.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h3 style="color: #4CAF50; margin-bottom: 10px;">🏠 Loan Details</h3>
                <div>Principal: <strong>$${data.principal.toLocaleString()}</strong></div>
                <div>Monthly Payment: <strong>$${data.monthlyPmt.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></div>
                <div>Initial Closing Costs: <strong>$${data.initialClosingCosts.toLocaleString()}</strong></div>
                <div>Cash at Closing: <strong>$${(data.downPayment + data.initialClosingCosts).toLocaleString()}</strong></div>
                <div>Total Cost (30yr): <strong>$${data.origTotal.toLocaleString()}</strong></div>
            </div>
            
            <div>
                <h3 style="color: #2196F3; margin-bottom: 10px;">🔄 Refinance Analysis</h3>
                <div>New Rate: <strong>${data.refiRate}%</strong></div>
                <div>Refinance at: <strong>Month ${data.refiMonth}</strong> (${years}y ${months}m)</div>
                <div>Total Cost with Refi: <strong>$${data.refiTotal.toLocaleString()}</strong></div>
                <div style="color: ${savingsColor}; font-size: 1.1em; margin-top: 10px;">
                    <strong>${savingsIcon} ${savingsText}: $${Math.abs(data.savings).toLocaleString()}</strong>
                </div>
            </div>
        `;
    }

    updateCharts(origSchedule, principal, origRate, refiRate, years, refiMonth, closingCostsPct) {
        this.updateBalanceChart(origSchedule);
        this.updatePaymentsChart(origSchedule);
        this.updateRefinanceChart(principal, origRate, refiRate, years, refiMonth, closingCostsPct, origSchedule);
        this.updateSavingsChart(principal, origRate, refiRate, years, closingCostsPct, origSchedule);
    }

    updateBalanceChart(schedule) {
        const ctx = this.balanceChart.getContext('2d');
        if (this.charts.balance) this.charts.balance.destroy();

        this.charts.balance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: schedule.map(p => p.month),
                datasets: [{ label: 'Loan Balance', data: schedule.map(p => p.balance), borderColor: '#4CAF50', backgroundColor: 'rgba(76,175,80,0.1)', fill: true }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Loan Balance Over Time', color: '#fff' } }, scales: { x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }, y: { ticks: { color: '#fff', callback: v => '$' + (v/1000).toFixed(0) + 'K' }, grid: { color: 'rgba(255,255,255,0.1)' } } } }
        });
    }

    updatePaymentsChart(schedule) {
        const ctx = this.paymentsChart.getContext('2d');
        if (this.charts.payments) this.charts.payments.destroy();

        this.charts.payments = new Chart(ctx, {
            type: 'line',
            data: {
                labels: schedule.map(p => p.month),
                datasets: [
                    { label: 'Principal', data: schedule.map(p => p.principalPayment), borderColor: '#2196F3', backgroundColor: 'rgba(33,150,243,0.1)', fill: true },
                    { label: 'Interest', data: schedule.map(p => p.interest), borderColor: '#FF5722', backgroundColor: 'rgba(255,87,34,0.1)', fill: true }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Monthly Principal vs Interest', color: '#fff' } }, scales: { x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }, y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } } } }
        });
    }

    updateRefinanceChart(principal, origRate, refiRate, years, refiMonth, closingCostsPct, origSchedule) {
        const ctx = this.refinanceChart.getContext('2d');
        if (this.charts.refinance) this.charts.refinance.destroy();

        const refiMonths = [];
        const totalCosts = [];
        const origTotal = origSchedule.reduce((sum, p) => sum + p.totalPayment, 0);

        for (let m = 1; m <= Math.min(origSchedule.length, 240); m += 6) {
            refiMonths.push(m);
            totalCosts.push(this.calculateRefinanceAnalysis(principal, origRate, refiRate, years, m, closingCostsPct));
        }

        this.charts.refinance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: refiMonths,
                datasets: [
                    { label: 'Cost w/ Refi', data: totalCosts, borderColor: '#9C27B0', fill: false },
                    { label: 'Original Cost', data: refiMonths.map(() => origTotal), borderColor: '#FF9800', borderDash: [5,5], fill: false }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Total Cost vs Refinance Timing', color: '#fff' } }, scales: { x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }, y: { ticks: { color: '#fff', callback: v => '$' + (v/1000).toFixed(0) + 'K' }, grid: { color: 'rgba(255,255,255,0.1)' } } } }
        });
    }

    updateSavingsChart(principal, origRate, refiRate, years, closingCostsPct, origSchedule) {
        const ctx = this.savingsChart.getContext('2d');
        if (this.charts.savings) this.charts.savings.destroy();

        const refiMonths = [];
        const savingsPos = [];
        const savingsNeg = [];
        const origTotal = origSchedule.reduce((sum, p) => sum + p.totalPayment, 0);

        for (let m = 1; m <= Math.min(origSchedule.length, 240); m += 6) {
            const cost = this.calculateRefinanceAnalysis(principal, origRate, refiRate, years, m, closingCostsPct);
            refiMonths.push(m);
            const diff = origTotal - cost;
            savingsPos.push(diff >= 0 ? diff : null);
            savingsNeg.push(diff < 0 ? diff : null);
        }

        this.charts.savings = new Chart(ctx, {
            type: 'line',
            data: {
                labels: refiMonths,
                datasets: [
                    { label: 'Savings', data: savingsPos, borderColor: '#4CAF50', backgroundColor: 'rgba(76,175,80,0.2)', fill: true, spanGaps: true },
                    { label: 'Additional Cost', data: savingsNeg, borderColor: '#F44336', backgroundColor: 'rgba(244,67,54,0.2)', fill: true, spanGaps: true }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Potential Savings by Refinance Month', color: '#fff' } }, scales: { x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }, y: { ticks: { color: '#fff', callback: v => '$' + (v/1000).toFixed(0) + 'K' }, grid: { color: 'rgba(255,255,255,0.1)' } } } }
        });
    }

    switchChart(chartType) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-chart="${chartType}"]`).classList.add('active');
        document.querySelectorAll('.chart-canvas').forEach(c => c.classList.remove('active'));
        document.getElementById(`${chartType}Chart`).classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', () => new MortgageCalculator());
