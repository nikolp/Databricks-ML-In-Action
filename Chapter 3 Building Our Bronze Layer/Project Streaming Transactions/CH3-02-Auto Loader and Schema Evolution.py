# Databricks notebook source
# MAGIC %md
# MAGIC Chapter 3: Building our Bronze Layer
# MAGIC
# MAGIC ## Streaming Data - Streaming as Delta into a table using Auto Loader + schema evolution
# MAGIC
# MAGIC When streaming directly into a Delta table the stream does not handle the schema change without intervention. You will have to restart the streaming query for it to notice the schema change. Otherwise it simply stops writing. Upon restart it will detect the change and need restarted again for a total of two restarts. 

# COMMAND ----------

# DBTITLE 1,Create Checkpoint and Schema reset widget
dbutils.widgets.dropdown(name='Reset', defaultValue='True', choices=['True', 'False'], label="Reset Checkpoint and Schema")

# COMMAND ----------

# MAGIC %md ##Run Setup

# COMMAND ----------

# MAGIC %run ../../global-setup $project_name=synthetic_transactions

# COMMAND ----------

# DBTITLE 1,Variables
table_name = "synthetic_transactions"
raw_data_location = f"{volume_file_path}/{table_name}/schema_change_data/"
schema_location = f"{volume_file_path}/{table_name}/schema"
checkpoint_location = f"{volume_file_path}/{table_name}/checkpoint"

# COMMAND ----------

# DBTITLE 1,Use to reset for fresh table, schema, checkpoints
if bool(dbutils.widgets.get('Reset')):
  dbutils.fs.rm(schema_location, True)
  dbutils.fs.rm(checkpoint_location, True)
  sql(f"DROP TABLE IF EXISTS {table_name}")

# COMMAND ----------

# DBTITLE 1,Optimization settings and reduce the number of files that must be read to determine schema
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", True)
spark.conf.set("spark.databricks.delta.autoCompact.enabled", True)
spark.conf.set("spark.databricks.cloudFiles.schemaInference.sampleSize.numFiles",1)
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", True)

# COMMAND ----------

# DBTITLE 1,Readstream
stream = spark.readStream \
  .format("cloudFiles") \
  .option("cloudFiles.format", "json") \
  .option("cloudFiles.schemaHints","CustomerID int, Amount double, TransactionTimestamp timestamp") \
  .option("cloudFiles.inferColumnTypes","true") \
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns") \
  .option("cloudFiles.schemaLocation", schema_location) \
  .load(raw_data_location) \
  .select("*") \
  .writeStream \
  .format("delta") \
  .outputMode("append") \
  .option("checkpointLocation", checkpoint_location) \
  .option("mergeSchema", "true") \
  .trigger(processingTime="10 seconds") \
  .toTable(tableName=table_name)

# COMMAND ----------

# DBTITLE 1,Viewing data in table while stream is running
# MAGIC %sql
# MAGIC SELECT * FROM synthetic_transactions ORDER BY TransactionTimestamp DESC LIMIT 10
