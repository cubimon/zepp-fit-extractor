package com.github.h3llk33p3r

import org.springframework.boot.CommandLineRunner
import org.springframework.stereotype.Component
import org.slf4j.LoggerFactory

import com.github.h3llk33p3r.command.ExporterCommands
import com.github.h3llk33p3r.MyCliTask
import java.io.File

@Component
class MyCliTask(private val exporterCommands: ExporterCommands) : CommandLineRunner {

    private val log = LoggerFactory.getLogger(MyCliTask::class.java)

    override fun run(vararg args: String) {
        val token = System.getenv("TOKEN")
            ?: throw IllegalStateException("Environment variable 'TOKEN' is required but was not found.")
        exporterCommands.downloadAll(token, File("./download"))
        exporterCommands.generateAll(File("./download"), File("./generated"))
    }
}
