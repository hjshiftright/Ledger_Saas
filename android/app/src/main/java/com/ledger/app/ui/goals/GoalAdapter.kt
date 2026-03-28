package com.ledger.app.ui.goals

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.R
import com.ledger.app.data.models.GoalOut
import com.ledger.app.databinding.ItemGoalCardBinding
import com.ledger.app.util.CurrencyFormatter

class GoalAdapter(
    private val onDeleteClick: ((GoalOut) -> Unit)? = null
) : ListAdapter<GoalOut, GoalAdapter.GoalViewHolder>(DIFF_CALLBACK) {

    inner class GoalViewHolder(private val binding: ItemGoalCardBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(goal: GoalOut) {
            binding.tvGoalName.text = goal.name
            binding.tvGoalType.text = goal.goal_type.replace("_", " ")

            val progress = goal.progress_pct.coerceIn(0.0, 100.0).toInt()
            binding.progressGoal.progress = progress

            // Progress bar color
            val progressColorRes = when {
                goal.progress_pct >= 75.0 -> R.color.emerald_500
                goal.progress_pct >= 40.0 -> R.color.indigo_500
                else -> R.color.amber_500
            }
            binding.progressGoal.progressTintList =
                android.content.res.ColorStateList.valueOf(
                    ContextCompat.getColor(binding.root.context, progressColorRes)
                )

            binding.tvProgressPct.text = "${progress}%"

            val current = goal.current_amount.toDoubleOrNull() ?: 0.0
            val target = goal.target_amount.toDoubleOrNull() ?: 0.0
            binding.tvCurrentAmount.text = CurrencyFormatter.format(current)
            binding.tvTargetAmount.text = "of ${CurrencyFormatter.format(target)}"

            binding.root.setOnLongClickListener {
                onDeleteClick?.invoke(goal)
                true
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): GoalViewHolder {
        val binding = ItemGoalCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return GoalViewHolder(binding)
    }

    override fun onBindViewHolder(holder: GoalViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        private val DIFF_CALLBACK = object : DiffUtil.ItemCallback<GoalOut>() {
            override fun areItemsTheSame(oldItem: GoalOut, newItem: GoalOut) =
                oldItem.id == newItem.id
            override fun areContentsTheSame(oldItem: GoalOut, newItem: GoalOut) =
                oldItem == newItem
        }
    }
}
