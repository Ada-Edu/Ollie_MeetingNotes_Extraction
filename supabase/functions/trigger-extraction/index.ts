/**
 * Supabase Edge Function: Trigger Meeting Notes Extraction Workflow
 *
 * This function serves as the bridge between the frontend and Temporal.
 * It receives meeting notes data and triggers the Temporal workflow.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.38.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface TriggerRequest {
  meeting_notes_id: string;
  notes_text: string;
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Parse request body
    const { meeting_notes_id, notes_text }: TriggerRequest = await req.json();

    if (!meeting_notes_id || !notes_text) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: meeting_notes_id, notes_text" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log(`[trigger-extraction] Received request for meeting_notes_id: ${meeting_notes_id}`);

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get Temporal configuration
    const temporalAddress = Deno.env.get("TEMPORAL_ADDRESS") || "temporal:7233";
    const taskQueue = Deno.env.get("TEMPORAL_TASK_QUEUE") || "main";

    console.log(`[trigger-extraction] Connecting to Temporal at ${temporalAddress}`);

    // For now, we'll use a direct HTTP call to a Python service that can trigger Temporal
    // This is because Deno doesn't have a native Temporal client
    const workerUrl = Deno.env.get("TEMPORAL_WORKER_URL") || "http://temporal-worker:8000";

    try {
      // Call the Python worker's HTTP endpoint to trigger workflow
      const response = await fetch(`${workerUrl}/trigger-workflow`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow_name: "ExtractMeetingActionItemsWorkflow",
          workflow_id: `extract-${meeting_notes_id}`,
          args: {
            meeting_notes_id,
            notes_text,
          },
          task_queue: taskQueue,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[trigger-extraction] Temporal trigger failed: ${errorText}`);

        // Update extraction_run status to failed
        await supabase
          .from("extraction_runs")
          .update({
            status: "failed",
            error_message: `Failed to trigger workflow: ${errorText}`,
            completed_at: new Date().toISOString(),
          })
          .eq("meeting_notes_id", meeting_notes_id)
          .order("created_at", { ascending: false })
          .limit(1);

        return new Response(
          JSON.stringify({
            error: "Failed to trigger workflow",
            details: errorText,
            meeting_notes_id
          }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      const result = await response.json();
      console.log(`[trigger-extraction] Workflow triggered successfully: ${JSON.stringify(result)}`);

      return new Response(
        JSON.stringify({
          success: true,
          meeting_notes_id,
          workflow_id: result.workflow_id || `extract-${meeting_notes_id}`,
          message: "Extraction workflow triggered successfully",
        }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );

    } catch (error) {
      console.error(`[trigger-extraction] Error calling worker:`, error);

      // Update extraction_run status to failed
      await supabase
        .from("extraction_runs")
        .update({
          status: "failed",
          error_message: `Worker connection error: ${error.message}`,
          completed_at: new Date().toISOString(),
        })
        .eq("meeting_notes_id", meeting_notes_id)
        .order("created_at", { ascending: false })
        .limit(1);

      return new Response(
        JSON.stringify({
          error: "Failed to connect to workflow service",
          details: error.message,
          meeting_notes_id
        }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

  } catch (error) {
    console.error("[trigger-extraction] Unexpected error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error", details: error.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
