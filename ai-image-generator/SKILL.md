---
name: ai-image-generator
description: Generate or edit images with Gemini and GPT image APIs using structured 5-part prompts (image type, subject, environment, camera specs, constraints). Use whenever the user asks to generate an image, create/edit a picture or graphic, needs a transparent-background icon or logo, wants a product/scene photo, or asks to refine an image across multiple turns. Covers model selection (Gemini for scenes/depth, GPT Image for transparent RGBA and text rendering), Python-based API calls (not curl), and vision-model QA of the output.
---

# AI Image Generator Skill Summary

This skill enables image generation using Gemini and GPT APIs with structured prompting patterns.

## Key Components

**Model Selection**: Gemini 3.1 Flash excels for scenes and depth; GPT Image 1.5 handles transparent icons and text rendering with native RGBA support.

**5-Part Framework**: Structure prompts as (1) image type, (2) subject details, (3) environment, (4) technical camera specs, (5) constraints/exclusions. Example: *"A professional skin treatment scene...practitioner wearing blue medical gloves uses a microneedling pen...Warm golden-hour light...Shot at 85mm f/2.0, shallow depth of field. No text, no watermarks."*

**API Implementation**: Python handles Gemini calls with proper escaping; separate approach for GPT's transparent background parameter.

**Multi-Turn Editing**: Preserve thought signatures from model responses when editing across conversation turns; specify what remains unchanged rather than just modifications.

**Quality Assurance**: Send generated images to vision models for artifact detection, technical accuracy, and composition review.

## Critical Warnings

- Don't use curl for Gemini—Python prevents shell escaping failures
- Verify current model IDs frequently; they change regularly
- Gemini cannot produce transparent PNGs; use GPT instead
- Replace generic praise ("beautiful, professional") with concrete technical parameters
- For Australian businesses, explicitly specify local context to avoid American defaults
