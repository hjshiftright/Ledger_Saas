package com.ledger.app.ui.reports

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.BarData
import com.github.mikephil.charting.data.BarDataSet
import com.github.mikephil.charting.data.BarEntry
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.data.models.MonthlyTrend
import com.ledger.app.databinding.FragmentReportsBinding
import com.ledger.app.util.CurrencyFormatter
import com.ledger.app.util.UiState
import com.ledger.app.util.gone
import com.ledger.app.util.show

class ReportsFragment : Fragment() {

    private var _binding: FragmentReportsBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: ReportsViewModel
    private lateinit var categoryAdapter: CategoryAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentReportsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewModel = ViewModelProvider(
            this,
            ReportsViewModelFactory(RetrofitClient.api)
        )[ReportsViewModel::class.java]

        categoryAdapter = CategoryAdapter()
        binding.rvCategories.adapter = categoryAdapter

        setupPeriodChips()
        setupObservers()

        // Default: This Month
        binding.chipThisMonth.isChecked = true
        viewModel.setPeriod("THIS_MONTH")
    }

    private fun setupPeriodChips() {
        binding.chipGroupPeriod.setOnCheckedStateChangeListener { group, checkedIds ->
            val period = when {
                binding.chipThisMonth.isChecked -> "THIS_MONTH"
                binding.chipLastMonth.isChecked -> "LAST_MONTH"
                binding.chipThisQuarter.isChecked -> "THIS_QUARTER"
                binding.chipThisYear.isChecked -> "THIS_YEAR"
                else -> "THIS_MONTH"
            }
            viewModel.setPeriod(period)
        }
    }

    private fun setupObservers() {
        viewModel.summaryState.observe(viewLifecycleOwner) { state ->
            if (state is UiState.Success) {
                val summary = state.data
                binding.tvKpiNetWorth.text = CurrencyFormatter.format(
                    summary.net_worth.toDoubleOrNull() ?: 0.0
                )
                binding.tvKpiIncome.text = CurrencyFormatter.format(
                    summary.period_income.toDoubleOrNull() ?: 0.0
                )
                binding.tvKpiExpense.text = CurrencyFormatter.format(
                    summary.period_expenses.toDoubleOrNull() ?: 0.0
                )
                binding.tvKpiSavingsRate.text = summary.savings_rate?.let {
                    "${String.format("%.1f", it)}%"
                } ?: "N/A"
            }
        }

        viewModel.trendState.observe(viewLifecycleOwner) { state ->
            if (state is UiState.Success) {
                updateBarChart(state.data)
            }
        }

        viewModel.categoriesState.observe(viewLifecycleOwner) { state ->
            if (state is UiState.Success) {
                categoryAdapter.submitList(state.data)
            }
        }
    }

    private fun updateBarChart(trends: List<MonthlyTrend>) {
        if (trends.isEmpty()) return

        val incomeEntries = trends.mapIndexed { idx, t ->
            BarEntry(idx.toFloat(), t.income.toFloatOrNull() ?: 0f)
        }
        val expenseEntries = trends.mapIndexed { idx, t ->
            BarEntry(idx.toFloat(), t.expense.toFloatOrNull() ?: 0f)
        }

        val incomeSet = BarDataSet(incomeEntries, "Income").apply {
            color = android.graphics.Color.parseColor("#059669")
        }
        val expenseSet = BarDataSet(expenseEntries, "Expenses").apply {
            color = android.graphics.Color.parseColor("#E11D48")
        }

        binding.barChart.apply {
            data = BarData(incomeSet, expenseSet).apply {
                barWidth = 0.35f
            }
            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.setDrawGridLines(false)
            axisLeft.setDrawGridLines(false)
            axisRight.isEnabled = false
            legend.isEnabled = true
            description.isEnabled = false
            groupBars(0f, 0.2f, 0.05f)
            invalidate()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
