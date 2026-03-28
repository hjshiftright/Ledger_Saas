package com.ledger.app.ui

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import androidx.lifecycle.LiveData
import androidx.lifecycle.Observer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Rule
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

abstract class BaseViewModelTest {

    @get:Rule
    val instantTaskRule = InstantTaskExecutorRule()

    protected val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUpDispatcher() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDownDispatcher() {
        Dispatchers.resetMain()
    }

    protected fun <T> LiveData<T>.getOrAwait(timeoutSeconds: Long = 2): T {
        var data: T? = null
        val latch = CountDownLatch(1)
        val observer = Observer<T> { value ->
            data = value
            latch.countDown()
        }
        observeForever(observer)
        latch.await(timeoutSeconds, TimeUnit.SECONDS)
        removeObserver(observer)
        @Suppress("UNCHECKED_CAST")
        return data as T
    }
}
