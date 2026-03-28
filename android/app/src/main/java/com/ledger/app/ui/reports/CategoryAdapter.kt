package com.ledger.app.ui.reports

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.data.models.ExpenseCategory
import com.ledger.app.databinding.ItemCategoryRowBinding
import com.ledger.app.util.CurrencyFormatter

class CategoryAdapter : ListAdapter<ExpenseCategory, CategoryAdapter.CategoryViewHolder>(DIFF) {

    inner class CategoryViewHolder(private val binding: ItemCategoryRowBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(category: ExpenseCategory) {
            binding.tvCategoryName.text = category.category
            binding.tvCategoryAmount.text = CurrencyFormatter.format(
                category.amount.toDoubleOrNull() ?: 0.0
            )
            binding.progressCategory.progress = category.percentage.coerceIn(0.0, 100.0).toInt()
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): CategoryViewHolder {
        val binding = ItemCategoryRowBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return CategoryViewHolder(binding)
    }

    override fun onBindViewHolder(holder: CategoryViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<ExpenseCategory>() {
            override fun areItemsTheSame(oldItem: ExpenseCategory, newItem: ExpenseCategory) =
                oldItem.category == newItem.category
            override fun areContentsTheSame(oldItem: ExpenseCategory, newItem: ExpenseCategory) =
                oldItem == newItem
        }
    }
}
