package com.ledger.app.ui.goals

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.databinding.FragmentGoalsBinding
import com.ledger.app.util.CurrencyFormatter
import com.ledger.app.util.UiState
import com.ledger.app.util.gone
import com.ledger.app.util.show

class GoalsFragment : Fragment() {

    private var _binding: FragmentGoalsBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: GoalsViewModel
    private lateinit var adapter: GoalAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentGoalsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewModel = ViewModelProvider(
            this,
            GoalsViewModelFactory(RetrofitClient.api)
        )[GoalsViewModel::class.java]

        setupAdapter()
        setupObservers()
        setupListeners()

        viewModel.loadGoals()
    }

    private fun setupAdapter() {
        adapter = GoalAdapter { goal ->
            AlertDialog.Builder(requireContext())
                .setTitle("Delete Goal")
                .setMessage("Are you sure you want to delete \"${goal.name}\"?")
                .setPositiveButton("Delete") { _, _ -> viewModel.deleteGoal(goal.id) }
                .setNegativeButton("Cancel", null)
                .show()
        }
        binding.rvGoals.adapter = adapter
    }

    private fun setupObservers() {
        viewModel.goalsState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is UiState.Loading -> {
                    binding.progressBar.show()
                    binding.layoutEmpty.gone()
                    binding.rvGoals.gone()
                }
                is UiState.Success -> {
                    binding.progressBar.gone()
                    if (state.data.isEmpty()) {
                        binding.layoutEmpty.show()
                        binding.rvGoals.gone()
                    } else {
                        binding.layoutEmpty.gone()
                        binding.rvGoals.show()
                        adapter.submitList(state.data)
                    }
                    updateSummary()
                }
                is UiState.Error -> {
                    binding.progressBar.gone()
                }
            }
        }
    }

    private fun updateSummary() {
        binding.tvGoalCount.text = "${(viewModel.goalsState.value as? UiState.Success)?.data?.size ?: 0}"
        binding.tvTotalTarget.text = CurrencyFormatter.format(viewModel.totalTargetAmount)
        binding.tvAvgProgress.text = "${String.format("%.0f", viewModel.averageProgress)}%"
    }

    private fun setupListeners() {
        binding.btnNewGoal.setOnClickListener {
            showCreateGoalDialog()
        }
        binding.btnCreateFirstGoal.setOnClickListener {
            showCreateGoalDialog()
        }
    }

    private fun showCreateGoalDialog() {
        // Simple dialog for goal creation - a full BottomSheet would go here in production
        android.widget.Toast.makeText(context, "Goal creation form coming soon", android.widget.Toast.LENGTH_SHORT).show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
