package com.ledger.app.ui.budgets

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.data.models.BudgetOut
import com.ledger.app.databinding.ItemBudgetCardBinding
import com.ledger.app.util.CurrencyFormatter

class BudgetAdapter(
    private val onDeleteClick: (BudgetOut) -> Unit
) : ListAdapter<BudgetOut, BudgetAdapter.BudgetViewHolder>(DIFF_CALLBACK) {

    inner class BudgetViewHolder(private val binding: ItemBudgetCardBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(budget: BudgetOut) {
            binding.tvBudgetName.text = budget.name
            binding.tvPeriodType.text = budget.period_type
            binding.tvDateRange.text = "${budget.start_date} — ${budget.end_date ?: "ongoing"}"

            // Calculate overall progress (total planned)
            val totalPlanned = budget.items.sumOf { it.planned_amount.toDoubleOrNull() ?: 0.0 }
            binding.tvBudgetName.setOnLongClickListener {
                onDeleteClick(budget)
                true
            }

            // Add line items
            binding.layoutLineItems.removeAllViews()
            budget.items.take(3).forEach { item ->
                val tv = android.widget.TextView(binding.root.context)
                tv.text = "${item.account_name}: ${CurrencyFormatter.format(item.planned_amount.toDoubleOrNull() ?: 0.0)}"
                tv.textSize = 12f
                tv.setPadding(0, 4, 0, 4)
                binding.layoutLineItems.addView(tv)
            }
            if (budget.items.size > 3) {
                val tv = android.widget.TextView(binding.root.context)
                tv.text = "+${budget.items.size - 3} more items"
                tv.textSize = 11f
                binding.layoutLineItems.addView(tv)
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BudgetViewHolder {
        val binding = ItemBudgetCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return BudgetViewHolder(binding)
    }

    override fun onBindViewHolder(holder: BudgetViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        private val DIFF_CALLBACK = object : DiffUtil.ItemCallback<BudgetOut>() {
            override fun areItemsTheSame(oldItem: BudgetOut, newItem: BudgetOut) =
                oldItem.id == newItem.id
            override fun areContentsTheSame(oldItem: BudgetOut, newItem: BudgetOut) =
                oldItem == newItem
        }
    }
}
