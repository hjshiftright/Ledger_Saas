package com.ledger.app.ui.dashboard

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.ledger.app.R
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.data.models.DashboardSummary
import com.ledger.app.data.models.GoalOut
import com.ledger.app.data.models.TransactionOut
import com.ledger.app.databinding.FragmentDashboardBinding
import com.ledger.app.ui.goals.GoalAdapter
import com.ledger.app.ui.transactions.TransactionAdapter
import com.ledger.app.util.CurrencyFormatter
import com.ledger.app.util.UiState
import com.ledger.app.util.gone
import com.ledger.app.util.show

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: DashboardViewModel
    private lateinit var goalAdapter: GoalAdapter
    private lateinit var transactionAdapter: TransactionAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewModel = ViewModelProvider(
            this,
            DashboardViewModelFactory(RetrofitClient.api)
        )[DashboardViewModel::class.java]

        setupRecyclerViews()
        setupObservers()
        setupListeners()

        viewModel.loadDashboard()
    }

    private fun setupRecyclerViews() {
        goalAdapter = GoalAdapter()
        binding.rvGoals.apply {
            layoutManager = LinearLayoutManager(context, LinearLayoutManager.HORIZONTAL, false)
            adapter = goalAdapter
        }

        transactionAdapter = TransactionAdapter()
        binding.rvRecentTransactions.apply {
            layoutManager = LinearLayoutManager(context)
            adapter = transactionAdapter
        }
    }

    private fun setupObservers() {
        viewModel.summaryState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is UiState.Loading -> showLoading(true)
                is UiState.Success -> {
                    showLoading(false)
                    bindSummary(state.data)
                }
                is UiState.Error -> {
                    showLoading(false)
                    showError(state.message)
                }
            }
        }

        viewModel.goalsState.observe(viewLifecycleOwner) { state ->
            if (state is UiState.Success) {
                goalAdapter.submitList(state.data)
            }
        }

        viewModel.transactionsState.observe(viewLifecycleOwner) { state ->
            if (state is UiState.Success) {
                transactionAdapter.submitList(state.data)
            }
        }
    }

    private fun setupListeners() {
        binding.swipeRefresh.setOnRefreshListener {
            viewModel.refresh()
            binding.swipeRefresh.isRefreshing = false
        }

        binding.tvViewAll.setOnClickListener {
            findNavController().navigate(R.id.transactionsFragment)
        }

        binding.btnRetry.setOnClickListener {
            binding.layoutError.gone()
            viewModel.loadDashboard()
        }
    }

    private fun bindSummary(summary: DashboardSummary) {
        binding.swipeRefresh.show()
        binding.layoutError.gone()

        val netWorth = summary.net_worth.toDoubleOrNull() ?: 0.0
        binding.tvNetWorth.text = CurrencyFormatter.format(netWorth)
        binding.tvNetWorth.setTextColor(
            resources.getColor(
                if (netWorth >= 0) com.ledger.app.R.color.indigo_700 else com.ledger.app.R.color.rose_600,
                null
            )
        )

        binding.tvTotalIncome.text = CurrencyFormatter.format(
            summary.period_income.toDoubleOrNull() ?: 0.0
        )
        binding.tvTotalExpense.text = CurrencyFormatter.format(
            summary.period_expenses.toDoubleOrNull() ?: 0.0
        )
    }

    private fun showLoading(loading: Boolean) {
        if (loading) {
            binding.layoutLoading.show()
            binding.layoutError.gone()
        } else {
            binding.layoutLoading.gone()
        }
    }

    private fun showError(message: String) {
        binding.swipeRefresh.gone()
        binding.layoutLoading.gone()
        binding.layoutError.show()
        binding.tvErrorMsg.text = message
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
