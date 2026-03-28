package com.ledger.app.ui.auth

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.data.models.TenantInfo
import com.ledger.app.databinding.ItemTenantBinding

class TenantAdapter(
    private val tenants: List<TenantInfo>,
    private val onTenantClick: (TenantInfo) -> Unit
) : RecyclerView.Adapter<TenantAdapter.TenantViewHolder>() {

    inner class TenantViewHolder(private val binding: ItemTenantBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(tenant: TenantInfo) {
            binding.tvTenantName.text = tenant.name
            binding.tvEntityType.text = tenant.entity_type
            binding.tvRole.text = tenant.role
            binding.root.setOnClickListener { onTenantClick(tenant) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TenantViewHolder {
        val binding = ItemTenantBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return TenantViewHolder(binding)
    }

    override fun onBindViewHolder(holder: TenantViewHolder, position: Int) {
        holder.bind(tenants[position])
    }

    override fun getItemCount(): Int = tenants.size
}
