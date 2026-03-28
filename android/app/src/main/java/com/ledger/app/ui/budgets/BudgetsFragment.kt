package com.ledger.app.ui.budgets

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.databinding.FragmentBudgetsBinding
import com.ledger.app.util.CurrencyFormatter
import com.ledger.app.util.UiState
import com.ledger.app.util.gone
import com.ledger.app.util.show

class BudgetsFragment : Fragment() {

    private var _binding: FragmentBudgetsBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: BudgetsViewModel
    private lateinit var adapter: BudgetAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentBudgetsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewModel = ViewModelProvider(
            this,
            BudgetsViewModelFactory(RetrofitClient.api)
        )[BudgetsViewModel::class.java]

        adapter = BudgetAdapter { budget ->
            AlertDialog.Builder(requireContext())
                .setTitle("Delete Budget")
                .setMessage("Deactivate \"${budget.name}\"?")
                .setPositiveButton("Delete") { _, _ -> viewModel.deleteBudget(budget.id) }
                .setNegativeButton("Cancel", null)
                .show()
        }
        binding.rvBudgets.adapter = adapter

        viewModel.budgetsState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is UiState.Loading -> {
                    binding.progressBar.show()
                    binding.layoutEmpty.gone()
                }
                is UiState.Success -> {
                    binding.progressBar.gone()
                    if (state.data.isEmpty()) {
                        binding.layoutEmpty.show()
                        binding.rvBudgets.gone()
                    } else {
                        binding.layoutEmpty.gone()
                        binding.rvBudgets.show()
                        adapter.submitList(state.data)
                    }
                    binding.tvBudgetCount.text = "${viewModel.activeBudgetCount}"
                    binding.tvTotalPlanned.text = CurrencyFormatter.format(viewModel.totalPlannedAmount)
                    binding.tvLineItems.text = "${viewModel.totalLineItems}"
                }
                is UiState.Error -> binding.progressBar.gone()
            }
        }

        binding.btnNewBudget.setOnClickListener {
            android.widget.Toast.makeText(context, "Budget creation form coming soon", android.widget.Toast.LENGTH_SHORT).show()
        }

        viewModel.loadBudgets()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
