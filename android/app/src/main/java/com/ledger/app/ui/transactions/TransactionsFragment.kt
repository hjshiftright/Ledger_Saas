package com.ledger.app.ui.transactions

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.databinding.FragmentTransactionsBinding
import com.ledger.app.util.UiState
import com.ledger.app.util.gone
import com.ledger.app.util.show

class TransactionsFragment : Fragment() {

    private var _binding: FragmentTransactionsBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: TransactionsViewModel
    private lateinit var adapter: TransactionAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentTransactionsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewModel = ViewModelProvider(
            this,
            TransactionsViewModelFactory(RetrofitClient.api)
        )[TransactionsViewModel::class.java]

        setupRecyclerView()
        setupObservers()

        viewModel.loadTransactions()
    }

    private fun setupRecyclerView() {
        adapter = TransactionAdapter()
        binding.rvTransactions.adapter = adapter
        binding.rvTransactions.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                super.onScrolled(recyclerView, dx, dy)
                val layoutManager = recyclerView.layoutManager as LinearLayoutManager
                val lastVisible = layoutManager.findLastVisibleItemPosition()
                val total = layoutManager.itemCount
                if (lastVisible >= total - 3 && viewModel.hasMorePages) {
                    viewModel.loadMore()
                }
            }
        })
    }

    private fun setupObservers() {
        viewModel.transactionState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is UiState.Loading -> {
                    binding.progressBar.show()
                    binding.layoutEmpty.gone()
                }
                is UiState.Success -> {
                    binding.progressBar.gone()
                    if (state.data.isEmpty()) {
                        binding.layoutEmpty.show()
                        binding.rvTransactions.gone()
                    } else {
                        binding.layoutEmpty.gone()
                        binding.rvTransactions.show()
                        adapter.submitList(state.data)
                    }
                    binding.tvCount.text = "Total: ${viewModel.totalCount}"
                }
                is UiState.Error -> {
                    binding.progressBar.gone()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
