package com.ledger.app.ui.transactions

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.R
import com.ledger.app.data.models.TransactionOut
import com.ledger.app.databinding.ItemTransactionRowBinding
import com.ledger.app.util.CurrencyFormatter

class TransactionAdapter : ListAdapter<TransactionOut, TransactionAdapter.ViewHolder>(DIFF_CALLBACK) {

    inner class ViewHolder(private val binding: ItemTransactionRowBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(transaction: TransactionOut) {
            // Parse date
            val dateParts = transaction.transaction_date.split("-")
            binding.tvDay.text = dateParts.getOrElse(2) { "" }
            binding.tvMonth.text = dateParts.getOrElse(1) { "" }
                .toIntOrNull()?.let { month ->
                    listOf("", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec").getOrElse(month) { "" }
                } ?: ""

            binding.tvDescription.text = transaction.description

            // Account names from lines
            val accounts = transaction.lines.map { it.account_name }.distinct().take(2).joinToString(" → ")
            binding.tvAccounts.text = accounts

            // Amount - show first CREDIT line amount
            val creditLine = transaction.lines.firstOrNull { it.line_type == "CREDIT" }
            val debitLine = transaction.lines.firstOrNull { it.line_type == "DEBIT" }
            val (amount, isCredit) = if (creditLine != null) {
                Pair(creditLine.amount.toDoubleOrNull() ?: 0.0, true)
            } else {
                Pair(debitLine?.amount?.toDoubleOrNull() ?: 0.0, false)
            }

            binding.tvAmount.text = CurrencyFormatter.format(amount)
            binding.tvAmount.setTextColor(
                ContextCompat.getColor(
                    binding.root.context,
                    if (isCredit) R.color.emerald_600 else R.color.rose_600
                )
            )

            binding.tvStatus.text = transaction.status
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTransactionRowBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        private val DIFF_CALLBACK = object : DiffUtil.ItemCallback<TransactionOut>() {
            override fun areItemsTheSame(oldItem: TransactionOut, newItem: TransactionOut) =
                oldItem.id == newItem.id
            override fun areContentsTheSame(oldItem: TransactionOut, newItem: TransactionOut) =
                oldItem == newItem
        }
    }
}
