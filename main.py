import os
import uuid
import razorpay

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

app = FastAPI(title="LookMatch AI")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini_api_key = os.getenv("GOOGLE_API_KEY")

if not gemini_api_key:
    raise RuntimeError("GOOGLE_API_KEY is missing from .env")

gemini_client = genai.Client(
    api_key=gemini_api_key
)


# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET")
    )
)


# ============================================================
# MOCK STORE INVENTORY
# ============================================================

# ============================================================
# MOCK STORE INVENTORY
# ============================================================

MOCK_INVENTORY = [

    {
        "id": "prod_1",
        "name": "Classic Black Leather Jacket",
        "price": 4500,
        "image": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80",
        "keywords": ["jacket", "leather", "black jacket", "coat"]
    },

    {
        "id": "prod_2",
        "name": "Minimalist White Cotton Tee",
        "price": 800,
        "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80",
        "keywords": ["tee", "tshirt", "t-shirt", "shirt", "white shirt", "white tee"]
    },

    {
        "id": "prod_3",
        "name": "Silver Stainless Steel Watch",
        "price": 3200,
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
        "keywords": ["watch", "wristwatch", "timepiece", "silver watch"]
    },

    {
        "id": "prod_4",
        "name": "Slim Fit Blue Denim Jeans",
        "price": 2200,
        "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=600&q=80",
        "keywords": ["jeans", "denim", "pants", "trousers", "blue jeans"]
    },

    {
        "id": "prod_5",
        "name": "Classic White Sneakers",
        "price": 3000,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80",
        "keywords": ["sneakers", "shoes", "footwear", "trainers", "white shoes"]
    },

    {
        "id": "prod_6",
        "name": "Premium Black Sunglasses",
        "price": 1500,
        "image": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=600&q=80",
        "keywords": ["sunglasses", "glasses", "eyewear", "shades"]
    },

    {
        "id": "prod_7",
        "name": "Minimal Black Leather Belt",
        "price": 900,
        "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "keywords": ["belt", "leather belt", "black belt"]
    },

    {
        "id": "prod_8",
        "name": "Urban Black Crossbody Bag",
        "price": 1800,
        "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=600&q=80",
        "keywords": ["bag", "crossbody", "handbag", "purse", "shoulder bag"]
    }

]


# ============================================================
# SHOP THE LOOK API
# ============================================================

@app.post("/api/shop-the-look")
async def shop_the_look(file: UploadFile = File(...)):

    try:

        # ----------------------------------------------------
        # 1. READ UPLOADED IMAGE
        # ----------------------------------------------------

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty."
            )

        # Get actual image MIME type
        mime_type = file.content_type or "image/jpeg"

        # Make sure it is an image
        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Please upload an image file."
            )


        # ----------------------------------------------------
        # 2. GEMINI VISION ANALYSIS
        # ----------------------------------------------------

        prompt = """
Analyze this outfit image carefully.

Identify ALL visible fashion items, including:

- tops
- t-shirts
- shirts
- jackets
- coats
- jeans
- trousers
- pants
- shoes
- sneakers
- watches
- sunglasses
- belts
- bags
- hats
- caps
- other visible accessories

Return ONLY simple fashion keywords separated by commas.

Example:

black jacket, white tee, blue jeans, sneakers, watch

Do not write sentences.
Do not use markdown.
Do not explain your answer.
"""


        # Convert uploaded bytes into a Gemini image Part
        image_part = types.Part.from_bytes(
            data=contents,
            mime_type=mime_type
        )


        # Send image + prompt to Gemini
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                prompt,
                image_part
            ]
        )


        # Get Gemini's text response
        ai_extracted_tags =  (response.text or "").strip().lower()


        # ----------------------------------------------------
        # 3. MATCH GEMINI TAGS WITH INVENTORY
        # ----------------------------------------------------

        matched_items = []
        total_original_price = 0

        for item in MOCK_INVENTORY:

            item_keywords = [
                keyword.lower()
                for keyword in item.get("keywords", [])
            ]

    # Check if any inventory keyword
    # appears in Gemini's detected tags
            if any(
                keyword in ai_extracted_tags
                for keyword in item_keywords
            ):

                matched_items.append(item)

                total_original_price += item["price"]

        # ----------------------------------------------------
        # 4. FALLBACK
        # ----------------------------------------------------

        if not matched_items:

            matched_items = [
                MOCK_INVENTORY[1],
                MOCK_INVENTORY[3],
                MOCK_INVENTORY[4],
                MOCK_INVENTORY[6]
            ]

            total_original_price = sum(
               item["price"]
               for item in matched_items
            )


        # ----------------------------------------------------
        # 5. APPLY 15% BUNDLE DISCOUNT
        # ----------------------------------------------------

        bundle_price_rupees = int(
            total_original_price * 0.85
        )


        # ----------------------------------------------------
        # 6. CREATE RAZORPAY ORDER
        # ----------------------------------------------------

        razorpay_order_payload = {

            # Razorpay expects amount in paise
            "amount": bundle_price_rupees * 100,

            "currency": "INR",

            "receipt": f"rcpt_{uuid.uuid4().hex[:10]}",

            "notes": {
                "bundled_products": ", ".join(
                    [
                        item["name"]
                        for item in matched_items
                    ]
                )
            }
        }


        # Create Razorpay order
        razorpay_order_response = (
            razorpay_client.order.create(
                data=razorpay_order_payload
            )
        )


        # ----------------------------------------------------
        # 7. SEND RESULT TO FRONTEND
        # ----------------------------------------------------

        return {

            "detected_tags": (
                ai_extracted_tags
                if ai_extracted_tags
                else "fashion look setup"
            ),

            "items_found": matched_items,

            "original_total": total_original_price,

            "bundle_total": bundle_price_rupees,

            "razorpay_order_id":
                razorpay_order_response["id"]
        }


    except HTTPException:
        raise


    except Exception as e:

        print("ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# FRONTEND
# ============================================================

@app.get("/", response_class=HTMLResponse)
def serve_frontend():

    razorpay_public_key = os.getenv(
        "RAZORPAY_KEY_ID",
        ""
    )


    html_content = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>LookMatch AI</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Razorpay Checkout -->
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>


    <style>

        * {
            box-sizing: border-box;
        }


        body {
            margin: 0;

            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            background:
                radial-gradient(
                    circle at 15% 10%,
                    rgba(99, 102, 241, 0.18),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 85% 15%,
                    rgba(236, 72, 153, 0.14),
                    transparent 28%
                ),
                #080b14;

            color: white;

            min-height: 100vh;
        }


        /* Glass card */

        .glass {
            background: rgba(255, 255, 255, 0.055);

            border: 1px solid rgba(255, 255, 255, 0.10);

            backdrop-filter: blur(20px);

            -webkit-backdrop-filter: blur(20px);
        }


        /* Gradient heading */

        .gradient-text {
            background:
                linear-gradient(
                    90deg,
                    #ffffff,
                    #c7d2fe,
                    #fbcfe8
                );

            -webkit-background-clip: text;
            background-clip: text;

            color: transparent;
        }


        /* Main card glow */

        .hero-glow {
            box-shadow:
                0 0 80px rgba(99, 102, 241, 0.12),
                inset 0 1px rgba(255, 255, 255, 0.05);
        }


        /* Upload area */

        .upload-box {
            transition: all 0.25s ease;
        }


        .upload-box:hover {
            border-color: rgba(129, 140, 248, 0.7);

            background: rgba(99, 102, 241, 0.07);

            transform: translateY(-2px);
        }


        /* Main button */

        .primary-btn {
            background:
                linear-gradient(
                    135deg,
                    #6366f1,
                    #8b5cf6
                );

            transition: all 0.25s ease;

            box-shadow:
                0 10px 30px rgba(99, 102, 241, 0.25);
        }


        .primary-btn:hover {
            transform: translateY(-2px);

            box-shadow:
                0 15px 40px rgba(99, 102, 241, 0.40);
        }


        .primary-btn:disabled {
            opacity: 0.55;

            cursor: not-allowed;

            transform: none;
        }


        /* Product cards */

        .product-card {
            transition: all 0.25s ease;
        }


        .product-card:hover {
            transform: translateY(-5px);

            border-color:
                rgba(129, 140, 248, 0.4);

            box-shadow:
                0 15px 40px rgba(0, 0, 0, 0.25);
        }


        /* AI scanning animation */

        .scan-line {
            position: absolute;

            left: 0;
            right: 0;

            height: 3px;

            background:
                linear-gradient(
                    90deg,
                    transparent,
                    #818cf8,
                    #f472b6,
                    transparent
                );

            box-shadow:
                0 0 20px #818cf8;

            animation:
                scan 2s linear infinite;
        }


        @keyframes scan {

            0% {
                top: 0;
            }

            50% {
                top: calc(100% - 3px);
            }

            100% {
                top: 0;
            }

        }


        /* Online status animation */

        .pulse-dot {
            animation:
                pulse 1.5s infinite;
        }


        @keyframes pulse {

            0%,
            100% {
                opacity: 0.4;

                transform: scale(0.9);
            }

            50% {
                opacity: 1;

                transform: scale(1);
            }

        }


        /* Fade animation */

        .fade-in {
            animation:
                fadeIn 0.5s ease forwards;
        }


        @keyframes fadeIn {

            from {
                opacity: 0;

                transform:
                    translateY(15px);
            }

            to {
                opacity: 1;

                transform:
                    translateY(0);
            }

        }


        /* AI tag */

        .tag {
            background:
                rgba(99, 102, 241, 0.12);

            border:
                1px solid rgba(129, 140, 248, 0.25);
        }


        /* Number circle */

        .number-circle {
            width: 34px;
            height: 34px;

            border-radius: 50%;

            display: flex;

            align-items: center;

            justify-content: center;

            background:
                rgba(99, 102, 241, 0.15);

            border:
                1px solid rgba(129, 140, 248, 0.3);
        }

    </style>

</head>


<body>


    <!-- ========================================================= -->
    <!-- HEADER -->
    <!-- ========================================================= -->

    <header class="max-w-7xl mx-auto px-6 pt-7">

        <div class="flex items-center justify-between">


            <!-- Logo -->

            <div class="flex items-center gap-3">

                <div
                    class="
                        w-10
                        h-10
                        rounded-xl
                        bg-gradient-to-br
                        from-indigo-500
                        to-purple-600
                        flex
                        items-center
                        justify-center
                        shadow-lg
                        shadow-indigo-500/20
                    "
                >

                    <span class="text-xl">
                        ✦
                    </span>

                </div>


                <div>

                    <div
                        class="
                            font-bold
                            text-xl
                            tracking-tight
                        "
                    >
                        LOOKMATCH
                    </div>


                    <div
                        class="
                            text-[10px]
                            text-gray-500
                            tracking-[0.25em]
                        "
                    >
                        AI FASHION
                    </div>

                </div>

            </div>


            <!-- Online Status -->

            <div
                class="
                    hidden
                    md:flex
                    items-center
                    gap-3
                    px-4
                    py-2
                    rounded-full
                    glass
                    text-sm
                    text-gray-300
                "
            >

                <span
                    class="
                        w-2
                        h-2
                        bg-emerald-400
                        rounded-full
                        pulse-dot
                    "
                ></span>

                AI stylist online

            </div>

        </div>

    </header>



    <!-- ========================================================= -->
    <!-- MAIN -->
    <!-- ========================================================= -->

    <main
        class="
            max-w-7xl
            mx-auto
            px-6
            py-14
        "
    >


        <!-- ===================================================== -->
        <!-- HERO -->
        <!-- ===================================================== -->

        <section
            class="
                text-center
                max-w-4xl
                mx-auto
            "
        >

            <div
                class="
                    inline-flex
                    items-center
                    gap-2
                    px-4
                    py-2
                    rounded-full
                    glass
                    text-sm
                    text-indigo-200
                    mb-7
                "
            >

                <span>
                    ✦
                </span>

                <span>
                    AI-powered visual shopping
                </span>

            </div>


            <h1
                class="
                    text-5xl
                    md:text-7xl
                    font-black
                    tracking-tight
                    leading-[0.95]
                "
            >

                Shop the Look.

                <br>

                <span class="gradient-text">
                    Instantly.
                </span>

            </h1>


            <p
                class="
                    mt-7
                    text-lg
                    md:text-xl
                    text-gray-400
                    max-w-2xl
                    mx-auto
                    leading-relaxed
                "
            >

                Upload any outfit inspiration and let AI
                deconstruct the style, discover matching
                products, and assemble your complete look.

            </p>

        </section>



        <!-- ===================================================== -->
        <!-- HOW IT WORKS -->
        <!-- ===================================================== -->

        <div
            class="
                max-w-3xl
                mx-auto
                mt-12
                grid
                grid-cols-3
                gap-3
            "
        >


            <!-- Step 1 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-4
                    text-center
                "
            >

                <div
                    class="
                        number-circle
                        mx-auto
                        mb-3
                    "
                >
                    1
                </div>


                <div class="text-sm font-semibold">
                    Upload
                </div>


                <div class="text-xs text-gray-500 mt-1">
                    Your inspiration
                </div>

            </div>



            <!-- Step 2 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-4
                    text-center
                "
            >

                <div
                    class="
                        number-circle
                        mx-auto
                        mb-3
                    "
                >
                    2
                </div>


                <div class="text-sm font-semibold">
                    Analyze
                </div>


                <div class="text-xs text-gray-500 mt-1">
                    AI finds the pieces
                </div>

            </div>



            <!-- Step 3 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-4
                    text-center
                "
            >

                <div
                    class="
                        number-circle
                        mx-auto
                        mb-3
                    "
                >
                    3
                </div>


                <div class="text-sm font-semibold">
                    Shop
                </div>


                <div class="text-xs text-gray-500 mt-1">
                    One complete bundle
                </div>

            </div>

        </div>



        <!-- ===================================================== -->
        <!-- MAIN WORKSPACE -->
        <!-- ===================================================== -->

        <section
            class="
                grid
                lg:grid-cols-2
                gap-7
                mt-12
            "
        >


            <!-- ================================================= -->
            <!-- LEFT SIDE - UPLOAD -->
            <!-- ================================================= -->

            <div
                class="
                    glass
                    hero-glow
                    rounded-3xl
                    p-7
                "
            >


                <!-- Heading -->

                <div
                    class="
                        flex
                        items-start
                        justify-between
                        mb-7
                    "
                >

                    <div>

                        <div
                            class="
                                text-xs
                                uppercase
                                tracking-[0.2em]
                                text-indigo-300
                                font-semibold
                                mb-2
                            "
                        >
                            Step 01
                        </div>


                        <h2 class="text-2xl font-bold">
                            Upload inspiration
                        </h2>


                        <p
                            class="
                                text-gray-400
                                text-sm
                                mt-2
                            "
                        >
                            Pinterest, Instagram or any
                            outfit image
                        </p>

                    </div>


                    <div class="text-3xl">
                        ◉
                    </div>

                </div>



                <!-- Upload Area -->

                <div
                    id="uploadArea"
                    class="
                        upload-box
                        relative
                        border-2
                        border-dashed
                        border-gray-700
                        rounded-2xl
                        min-h-[420px]
                        flex
                        flex-col
                        items-center
                        justify-center
                        text-center
                        p-6
                        cursor-pointer
                    "
                >


                    <!-- File Input -->

                    <input
                        id="fileInput"
                        type="file"
                        accept="image/*"
                        class="hidden"
                    >



                    <!-- Upload Placeholder -->

                    <div id="uploadPlaceholder">

                        <div
                            class="
                                w-20
                                h-20
                                rounded-3xl
                                bg-indigo-500/10
                                border
                                border-indigo-400/20
                                flex
                                items-center
                                justify-center
                                mx-auto
                                mb-6
                            "
                        >

                            <span class="text-4xl">
                                ↑
                            </span>

                        </div>


                        <h3 class="text-lg font-semibold">
                            Drop your outfit here
                        </h3>


                        <p
                            class="
                                text-gray-500
                                text-sm
                                mt-2
                            "
                        >
                            or choose an image from your device
                        </p>


                        <button
                            type="button"
                            onclick="
                                document
                                .getElementById('fileInput')
                                .click()
                            "
                            class="
                                mt-6
                                px-6
                                py-3
                                rounded-xl
                                bg-white
                                text-black
                                font-semibold
                                text-sm
                                hover:bg-gray-200
                                transition
                            "
                        >
                            Choose Image
                        </button>


                        <p
                            class="
                                text-xs
                                text-gray-600
                                mt-5
                            "
                        >
                            JPG, PNG or WEBP
                        </p>

                    </div>



                    <!-- Image Preview -->

                    <div
                        id="previewContainer"
                        class="hidden w-full"
                    >

                        <div
                            class="
                                relative
                                max-h-[360px]
                                rounded-2xl
                                overflow-hidden
                                bg-black
                            "
                        >

                            <img
                                id="previewImage"
                                class="
                                    w-full
                                    max-h-[360px]
                                    object-contain
                                "
                                alt="Outfit preview"
                            >


                            <!-- AI Scan Effect -->

                            <div
                                id="scanEffect"
                                class="hidden absolute inset-0"
                            >

                                <div class="scan-line"></div>

                            </div>

                        </div>


                        <div
                            id="selectedFileName"
                            class="
                                text-sm
                                text-gray-400
                                mt-4
                            "
                        ></div>

                    </div>

                </div>



                <!-- Analyze Button -->

                <button
                    id="analyzeBtn"
                    class="
                        primary-btn
                        w-full
                        mt-6
                        py-4
                        rounded-2xl
                        font-bold
                        text-base
                    "
                >

                    ✦ Deconstruct & Assemble My Look

                </button>

            </div>



            <!-- ================================================= -->
            <!-- RIGHT SIDE - RESULTS -->
            <!-- ================================================= -->

            <div
                id="resultsContainer"
                class="
                    glass
                    hero-glow
                    rounded-3xl
                    p-7
                    min-h-[500px]
                "
            >


                <!-- Empty State -->

                <div
                    id="emptyResults"
                    class="
                        h-full
                        min-h-[450px]
                        flex
                        flex-col
                        items-center
                        justify-center
                        text-center
                    "
                >

                    <div
                        class="
                            w-24
                            h-24
                            rounded-full
                            bg-gradient-to-br
                            from-indigo-500/10
                            to-pink-500/10
                            border
                            border-white/10
                            flex
                            items-center
                            justify-center
                            mb-7
                        "
                    >

                        <span class="text-4xl">
                            ✦
                        </span>

                    </div>


                    <div class="text-xl font-bold">
                        Your look will appear here
                    </div>


                    <p
                        class="
                            text-gray-500
                            text-sm
                            max-w-sm
                            mt-3
                            leading-relaxed
                        "
                    >
                        Upload an outfit and our AI stylist
                        will identify the key pieces and
                        build a shoppable collection.
                    </p>

                </div>



                <!-- Result Content -->

                <div
                    id="resultContent"
                    class="
                        hidden
                        fade-in
                    "
                >


                    <!-- Result Header -->

                    <div
                        class="
                            flex
                            items-start
                            justify-between
                            mb-7
                        "
                    >

                        <div>

                            <div
                                class="
                                    text-xs
                                    uppercase
                                    tracking-[0.2em]
                                    text-indigo-300
                                    font-semibold
                                    mb-2
                                "
                            >
                                AI Analysis
                            </div>


                            <h2 class="text-2xl font-bold">
                                Your look is ready
                            </h2>

                        </div>


                        <div
                            class="
                                px-3
                                py-1.5
                                rounded-full
                                bg-emerald-500/10
                                border
                                border-emerald-400/20
                                text-emerald-300
                                text-xs
                            "
                        >
                            MATCH FOUND
                        </div>

                    </div>



                    <!-- AI Tags -->

                    <div class="mb-8">

                        <div
                            class="
                                text-xs
                                text-gray-500
                                uppercase
                                tracking-widest
                                mb-3
                            "
                        >
                            Detected style
                        </div>


                        <div
                            id="aiTags"
                            class="
                                flex
                                flex-wrap
                                gap-2
                            "
                        ></div>

                    </div>



                    <!-- Matched Products -->

                    <div>

                        <div
                            class="
                                flex
                                items-center
                                justify-between
                                mb-4
                            "
                        >

                            <div
                                class="
                                    text-xs
                                    text-gray-500
                                    uppercase
                                    tracking-widest
                                "
                            >
                                Matched pieces
                            </div>


                            <div
                                id="itemCount"
                                class="
                                    text-xs
                                    text-gray-500
                                "
                            ></div>

                        </div>


                        <div
                            id="matchedItems"
                            class="
                                grid
                                grid-cols-1
                                sm:grid-cols-2
                                gap-3
                            "
                        ></div>

                    </div>



                    <!-- Pricing -->

                    <div
                        class="
                            mt-7
                            pt-6
                            border-t
                            border-white/10
                        "
                    >


                        <!-- Original Price -->

                        <div
                            class="
                                flex
                                justify-between
                                text-sm
                                text-gray-400
                                mb-2
                            "
                        >

                            <span>
                                Original collection
                            </span>


                            <span id="subtotal">
                                ₹0
                            </span>

                        </div>



                        <!-- Discount -->

                        <div
                            class="
                                flex
                                justify-between
                                text-sm
                                text-emerald-400
                                mb-3
                            "
                        >

                            <span>
                                AI bundle discount
                            </span>


                            <span id="discount">
                                -₹0
                            </span>

                        </div>



                        <!-- Final Price -->

                        <div
                            class="
                                flex
                                justify-between
                                items-end
                            "
                        >

                            <div>

                                <div
                                    class="
                                        text-xs
                                        text-gray-500
                                    "
                                >
                                    COMPLETE LOOK
                                </div>


                                <div
                                    class="
                                        text-3xl
                                        font-black
                                        mt-1
                                    "
                                >

                                    <span id="finalPrice">
                                        ₹0
                                    </span>

                                </div>

                            </div>


                            <div
                                class="
                                    text-xs
                                    text-gray-500
                                "
                            >
                                Bundle price
                            </div>

                        </div>



                        <!-- Checkout -->

                        <button
                            id="checkoutBtn"
                            onclick="checkout()"
                            class="
                                primary-btn
                                w-full
                                mt-6
                                py-4
                                rounded-2xl
                                font-bold
                                text-base
                            "
                        >
                            Get This Look →
                        </button>

                    </div>

                </div>

            </div>

        </section>



        <!-- ===================================================== -->
        <!-- FEATURES -->
        <!-- ===================================================== -->

        <section
            class="
                grid
                md:grid-cols-3
                gap-4
                mt-7
            "
        >


            <!-- Feature 1 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-5
                "
            >

                <div class="text-2xl mb-3">
                    ◈
                </div>


                <div class="font-semibold">
                    Visual AI
                </div>


                <p
                    class="
                        text-xs
                        text-gray-500
                        mt-2
                        leading-relaxed
                    "
                >
                    Understands clothing directly from
                    your inspiration image.
                </p>

            </div>



            <!-- Feature 2 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-5
                "
            >

                <div class="text-2xl mb-3">
                    ◆
                </div>


                <div class="font-semibold">
                    Smart Bundles
                </div>


                <p
                    class="
                        text-xs
                        text-gray-500
                        mt-2
                        leading-relaxed
                    "
                >
                    Combines matching products into one
                    convenient collection.
                </p>

            </div>



            <!-- Feature 3 -->

            <div
                class="
                    glass
                    rounded-2xl
                    p-5
                "
            >

                <div class="text-2xl mb-3">
                    ✓
                </div>


                <div class="font-semibold">
                    One-Tap Checkout
                </div>


                <p
                    class="
                        text-xs
                        text-gray-500
                        mt-2
                        leading-relaxed
                    "
                >
                    Move from inspiration to purchase
                    without rebuilding the look yourself.
                </p>

            </div>

        </section>

    </main>



    <!-- ========================================================= -->
    <!-- FOOTER -->
    <!-- ========================================================= -->

    <footer
        class="
            max-w-7xl
            mx-auto
            px-6
            pb-10
            pt-5
            border-t
            border-white/5
        "
    >

        <div
            class="
                flex
                flex-col
                md:flex-row
                justify-between
                gap-3
                text-xs
                text-gray-600
            "
        >

            <span>
                LOOKMATCH AI
            </span>


            <span>
                Turn inspiration into a shoppable look.
            </span>

        </div>

    </footer>



    <!-- ========================================================= -->
    <!-- JAVASCRIPT -->
    <!-- ========================================================= -->

    <script>

         window.razorpayPublicKey =
        "__RAZORPAY_KEY_ID__";
        /* ===================================================== */
        /* ELEMENTS */
        /* ===================================================== */

        const fileInput =
            document.getElementById("fileInput");

        const uploadArea =
            document.getElementById("uploadArea");

        const analyzeBtn =
            document.getElementById("analyzeBtn");

        const previewImage =
            document.getElementById("previewImage");

        const previewContainer =
            document.getElementById("previewContainer");

        const uploadPlaceholder =
            document.getElementById("uploadPlaceholder");

        const resultContent =
            document.getElementById("resultContent");

        const emptyResults =
            document.getElementById("emptyResults");

        const scanEffect =
            document.getElementById("scanEffect");

        const selectedFileName =
            document.getElementById("selectedFileName");



        /* ===================================================== */
        /* FILE SELECTION */
        /* ===================================================== */

        fileInput.addEventListener(
            "change",
            function () {

                const file =
                    this.files[0];

                if (!file) {
                    return;
                }

                showPreview(file);

            }
        );



        /* ===================================================== */
        /* DRAG OVER */
        /* ===================================================== */

        uploadArea.addEventListener(
            "dragover",
            function (event) {

                event.preventDefault();

                uploadArea.classList.add(
                    "border-indigo-400",
                    "bg-indigo-500/10"
                );

            }
        );



        /* ===================================================== */
        /* DRAG LEAVE */
        /* ===================================================== */

        uploadArea.addEventListener(
            "dragleave",
            function () {

                uploadArea.classList.remove(
                    "border-indigo-400",
                    "bg-indigo-500/10"
                );

            }
        );



        /* ===================================================== */
        /* DROP IMAGE */
        /* ===================================================== */

        uploadArea.addEventListener(
            "drop",
            function (event) {

                event.preventDefault();

                uploadArea.classList.remove(
                    "border-indigo-400",
                    "bg-indigo-500/10"
                );


                const file =
                    event.dataTransfer.files[0];


                if (!file) {
                    return;
                }


                if (!file.type.startsWith("image/")) {

                    alert(
                        "Please upload an image file."
                    );

                    return;
                }


                fileInput.files =
                    event.dataTransfer.files;


                showPreview(file);

            }
        );



        /* ===================================================== */
        /* SHOW PREVIEW */
        /* ===================================================== */

        function showPreview(file) {

            const imageUrl =
                URL.createObjectURL(file);


            previewImage.src =
                imageUrl;


            uploadPlaceholder.classList.add(
                "hidden"
            );


            previewContainer.classList.remove(
                "hidden"
            );


            selectedFileName.innerText =
                file.name +
                " • Ready for AI analysis";


            resultContent.classList.add(
                "hidden"
            );


            emptyResults.classList.remove(
                "hidden"
            );

        }



        /* ===================================================== */
        /* ANALYZE BUTTON */
        /* ===================================================== */

        analyzeBtn.addEventListener(
            "click",
            async function () {

                if (!fileInput.files.length) {

                    alert(
                        "Please upload an outfit image first."
                    );

                    return;
                }


                analyzeBtn.disabled =
                    true;


                analyzeBtn.innerText =
                    "✦ AI is deconstructing your look...";


                scanEffect.classList.remove(
                    "hidden"
                );


                try {

                    const formData =
                        new FormData();


                    formData.append(
                        "file",
                        fileInput.files[0]
                    );


                    const response =
                        await fetch(
                            "/api/shop-the-look",
                            {
                                method: "POST",
                                body: formData
                            }
                        );


                    const data =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            data.detail ||
                            "Something went wrong."
                        );

                    }


                    renderResults(data);

                }

                catch (error) {

                    resultContent.classList.add(
                        "hidden"
                    );


                    emptyResults.classList.remove(
                        "hidden"
                    );


                    emptyResults.innerHTML = `

                        <div
                            class="
                                w-20
                                h-20
                                rounded-full
                                bg-red-500/10
                                border
                                border-red-400/20
                                flex
                                items-center
                                justify-center
                                mb-5
                            "
                        >

                            <span class="text-3xl">
                                !
                            </span>

                        </div>


                        <div
                            class="
                                text-xl
                                font-bold
                                text-red-300
                            "
                        >
                            Backend Error
                        </div>


                        <p
                            class="
                                text-sm
                                text-gray-400
                                max-w-md
                                mt-3
                            "
                        >
                            ${error.message}
                        </p>

                    `;

                }

                finally {

                    scanEffect.classList.add(
                        "hidden"
                    );


                    analyzeBtn.disabled =
                        false;


                    analyzeBtn.innerText =
                        "✦ Deconstruct & Assemble My Look";

                }

            }
        );



        /* ===================================================== */
        /* RENDER RESULTS */
        /* ===================================================== */

        function renderResults(data) {

            emptyResults.classList.add(
                "hidden"
            );


            resultContent.classList.remove(
                "hidden"
            );


            resultContent.classList.add(
                "fade-in"
            );



            /* --------------------------------------------- */
            /* AI TAGS */
            /* --------------------------------------------- */

            const aiTags =
                document.getElementById(
                    "aiTags"
                );


            aiTags.innerHTML =
                "";


            const tagString =
                 data.detected_tags ||
                 "";


            const tags =
                tagString.split(",");


            tags.forEach(
                function (tag) {

                    tag =
                        tag.trim();


                    if (!tag) {
                        return;
                    }


                    const span =
                        document.createElement(
                            "span"
                        );


                    span.className =
                        `
                            tag
                            px-3
                            py-1.5
                            rounded-full
                            text-xs
                            text-indigo-200
                        `;


                    span.innerText =
                        tag;


                    aiTags.appendChild(
                        span
                    );

                }
            );



            /* --------------------------------------------- */
            /* PRODUCTS */
            /* --------------------------------------------- */

            const matchedItems =
                document.getElementById(
                    "matchedItems"
                );


            matchedItems.innerHTML =
                "";


            const items =
                data.items_found ||
                [];


            document.getElementById(
                "itemCount"
            ).innerText =
                items.length +
                " pieces";



            items.forEach(
                function (item) {

                    const card =
                        document.createElement(
                            "div"
                        );


                    card.className =
                        `
                            product-card
                            glass
                            rounded-2xl
                            p-3
                        `;


                    card.innerHTML = `

                        <div
                            class="
                                aspect-square
                                rounded-xl
                                overflow-hidden
                                bg-gray-900
                                mb-3
                                border
                                border-white/5
                            "
                        >

                            <img
                                src="${item.image}"
                                alt="${item.name}"
                                class="
                                    w-full
                                    h-full
                                    object-cover
                                    transition
                                    duration-300
                                    hover:scale-105
                                "
                                loading="lazy"
                            >

                        </div>


                        <div class="px-1">

                            <div
                                class="
                                    text-sm
                                    font-semibold
                                    leading-snug
                                "
                            >
                                ${item.name}
                            </div>


                            <div
                                class="
                                    text-indigo-300
                                    font-bold
                                    mt-2
                                "
                            >
                                ₹${Number(item.price)
                                    .toLocaleString("en-IN")}
                            </div>

                         </div>

                    `;


                    matchedItems.appendChild(
                        card
                    );

                }
            );



            /* --------------------------------------------- */
            /* PRICES */
            /* --------------------------------------------- */

            const subtotal =
                data.original_total ??
                0;


            const finalPrice =
                data.bundle_total ??
                0;


            const discount =
                subtotal -
                finalPrice;



            document.getElementById(
                "subtotal"
            ).innerText =
                "₹" +
                Number(subtotal)
                    .toLocaleString("en-IN");



            document.getElementById(
                "discount"
            ).innerText =
                "-₹" +
                Number(discount)
                    .toLocaleString("en-IN");



            document.getElementById(
                "finalPrice"
            ).innerText =
                "₹" +
                Number(finalPrice)
                    .toLocaleString("en-IN");
            window.bundleAmount =
                Number(finalPrice);

            window.razorpayOrderId =
                data.razorpay_order_id;
        } 

    /* ===================================================== */
/* RAZORPAY CHECKOUT */
/* ===================================================== */

function checkout() {

    if (!window.Razorpay) {

        alert(
            "Razorpay Checkout failed to load."
        );

        return;
    }

    if (!window.razorpayOrderId) {

        alert(
            "Order information is missing."
        );

        return;
    }

    const checkoutBtn =
        document.getElementById("checkoutBtn");

    checkoutBtn.disabled = true;

    checkoutBtn.innerText =
        "Opening secure checkout...";


    const options = {

        key: window.razorpayPublicKey,

        amount:
            window.bundleAmount * 100,

        currency: "INR",

        name: "LOOKMATCH",

        description:
            "AI Curated Fashion Bundle",

        order_id:
            window.razorpayOrderId,
        hidden: {
            contact: true
        },
        theme: {
            color: "#6366f1"
        },


        handler: function (response) {

            alert(
                "Payment successful! 🎉"
            );

            console.log(
                "Payment response:",
                response
            );

        },


        modal: {

            ondismiss: function () {

                checkoutBtn.disabled =
                    false;

                checkoutBtn.innerText =
                    "Get This Look →";

            }

        }

    };


    try {

        const razorpay =
            new Razorpay(options);

        razorpay.open();

    }

    catch (error) {

        console.error(
            "Checkout error:",
            error
        );

        alert(
            "Unable to open Razorpay Checkout."
        );

        checkoutBtn.disabled =
            false;

        checkoutBtn.innerText =
            "Get This Look →";

    }

}
    </script>

</body>

</html>
"""
    html_content = html_content.replace(
        "__RAZORPAY_KEY_ID__",
        razorpay_public_key
    )


    return HTMLResponse(content=html_content)