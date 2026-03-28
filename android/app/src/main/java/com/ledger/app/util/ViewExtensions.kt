package com.ledger.app.util

import android.graphics.Color
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.ledger.app.R

fun View.show() {
    visibility = View.VISIBLE
}

fun View.hide() {
    visibility = View.INVISIBLE
}

fun View.gone() {
    visibility = View.GONE
}

fun TextView.setAmountText(amount: Double, showSign: Boolean = false) {
    val formatted = CurrencyFormatter.format(kotlin.math.abs(amount))
    text = if (showSign && amount < 0) "-$formatted" else formatted
    setTextColor(
        ContextCompat.getColor(
            context,
            if (amount >= 0) R.color.emerald_600 else R.color.rose_600
        )
    )
}

fun ProgressBar.setProgressColor(percent: Double) {
    val colorRes = when {
        percent >= 75.0 -> R.color.emerald_500
        percent >= 40.0 -> R.color.indigo_500
        else -> R.color.amber_500
    }
    progressTintList = android.content.res.ColorStateList.valueOf(
        ContextCompat.getColor(context, colorRes)
    )
}
