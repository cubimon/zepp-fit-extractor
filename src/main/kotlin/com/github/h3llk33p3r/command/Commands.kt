package com.github.h3llk33p3r.command

import com.fasterxml.jackson.module.kotlin.readValue
import com.github.h3llk33p3r.Utils.Companion.MAPPER
import com.github.h3llk33p3r.Utils.Companion.SUMMARIES_FILENAME
import com.github.h3llk33p3r.Utils.Companion.ZEPP_BASE_URL
import com.github.h3llk33p3r.client.SportDetail
import com.github.h3llk33p3r.client.SportSummary
import com.github.h3llk33p3r.client.ZeppRestClient
import com.github.h3llk33p3r.io.ActivityType
import com.github.h3llk33p3r.service.FitConverter
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import java.io.File

@Component
class ExporterCommands {

    private val converter = FitConverter()
    private val logger = LoggerFactory.getLogger(ExporterCommands::class.java)

    fun downloadAll(
        token: String,
        outputDirectory: File,
    ) {

        checkAndCreateOutDirectory(outputDirectory)
        logger.info("Starting download")
        val client = ZeppRestClient(ZEPP_BASE_URL, token)
        val summaries = client.summaries
        //Write to file
        MAPPER.writeValue(File(outputDirectory, SUMMARIES_FILENAME), summaries)
        summaries.forEach {
            val f = File(outputDirectory, "${it.trackid}.json")
            if (!f.exists()) {
                val detail = client.getDetail(it)
                MAPPER.writeValue(f, detail)
            }
        }

        logger.info("All resources have been downloaded")
    }

    private fun checkAndCreateOutDirectory(outputDirectory: File) {
        if (!outputDirectory.exists()) {
            if (!outputDirectory.mkdirs()) {
                throw RuntimeException("Unable to create the output directory [${outputDirectory.absolutePath}]")
            }
        } else if (!outputDirectory.isDirectory) {
            throw RuntimeException("The targeted output is not a directory [${outputDirectory.absolutePath}]")
        }
    }

    fun generateAll(
        inputDir: File,
        outputDirectory: File
    ) {

        val summariesFile = File(inputDir, SUMMARIES_FILENAME)
        if (!summariesFile.exists()) {
            throw RuntimeException("The target input directory does not contains the summaries file. Please check your command -i option.")
        }
        checkAndCreateOutDirectory(outputDirectory)
        val summaries = MAPPER.readValue<List<SportSummary>>(summariesFile)
        logger.info("There is ${summaries.size} activity loaded from summaries file")
        generateFor(summaries, inputDir, outputDirectory)

    }

    private fun generateFor(
        summaries: List<SportSummary>,
        inputDir: File,
        outputDirectory: File
    ) {
        summaries.forEach { sumary ->
            val detailFile = File(inputDir, "${sumary.trackid}.json")
            val detail = MAPPER.readValue<SportDetail>(detailFile)
            val result = converter.convertToFit(outputDirectory, sumary, detail)
            result?.let { logger.info("Activity {} has been saved into {}", detail.trackid, it.absoluteFile) }
        }
    }

    fun generateSingle(
        inputDir: File,
        outputDirectory: File,
        trackId: String
    ) {

        val summariesFile = File(inputDir, SUMMARIES_FILENAME)
        if (!summariesFile.exists()) {
            throw RuntimeException("The target input directory does not contains the summaries file. Please check your command -i option.")
        }
        checkAndCreateOutDirectory(outputDirectory)
        val summaries = MAPPER.readValue<List<SportSummary>>(summariesFile)
        val summary = summaries.find { it.trackid == trackId }
        if (summary != null) {
            generateFor(listOf(summary), inputDir, outputDirectory)
        }
    }

    fun generateForSport(
        inputDir: File,
        outputDirectory: File,
        sportType: ActivityType
    ) {

        val summariesFile = File(inputDir, SUMMARIES_FILENAME)
        if (!summariesFile.exists()) {
            throw RuntimeException("The target input directory does not contains the summaries file. Please check your command -i option.")
        }
        checkAndCreateOutDirectory(outputDirectory)
        val summaries = MAPPER.readValue<List<SportSummary>>(summariesFile)
        val filtered = summaries.filter { ActivityType.fromZepp(it.type) == sportType }.toList()
        generateFor(filtered, inputDir, outputDirectory)
    }

}
