#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <time.h>
#include <cjson/cJSON.h>
#include <libxml/HTMLparser.h>
#include <libxml/xpath.h>
#include <libxml/xpathInternals.h>
#include <math.h>
#include "config.h"

struct url_mem {
    char *memory;
    size_t size;
};
typedef struct {
    double *rates;
    char **dates;
    int size;
} HistoricalData; //currency

typedef struct {
    char date[11];
    double open;
    double high;
    double low;
    double close;
    double volume;
} StockHistoricalData;

typedef struct {
    char date[11];
    double value;
} PriceIndexData; //inflation

typedef struct {
    char year[5];
    double value;
} EconomicData; //GDP, unemployment

typedef struct {
    char date[11];
    double value;
} InterestRateData;

void free_memory(void *ptr) {
    free(ptr);
}

// callback function to handle data received from an HTTP request
static size_t write_memory_callback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t realsize = size * nmemb; // calc  size of  data received
    struct url_mem *mem = (struct url_mem *)userp;
    char *ptr = realloc(mem->memory, mem->size + realsize + 1); // reallocate memory to accommodate the new data
    if (!ptr) return printf("realloc failed\n"), 0;
    mem->memory = ptr; // update ptr to new memory location
    memcpy(&(mem->memory[mem->size]), contents, realsize); // copy new data to the end of the existing buffer
    mem->size += realsize; //update size of buffer
    mem->memory[mem->size] = 0; //null terminate buffer
    return realsize;
}

// start curl session and set up headers
CURL* initialize_curl(struct url_mem *chunk, const char *url, struct curl_slist *headers) {
    CURL *curl_handle;
    if (!(curl_handle = curl_easy_init())) return (fprintf(stderr, "couldn't start CURL\n"), NULL);

    curl_easy_setopt(curl_handle, CURLOPT_URL, url); // set url
    curl_easy_setopt(curl_handle, CURLOPT_WRITEFUNCTION, write_memory_callback); //setup callback
    curl_easy_setopt(curl_handle, CURLOPT_WRITEDATA, (void *)chunk); // pass chunk to callback, to store data received

    if (headers) {
        curl_easy_setopt(curl_handle, CURLOPT_HTTPHEADER, headers);}
    return curl_handle;
}

void cleanup_curl(CURL *curl_handle, struct curl_slist *headers, struct url_mem *chunk) {
    if (chunk->memory) free(chunk->memory);
    if (headers) curl_slist_free_all(headers);
    if (curl_handle) curl_easy_cleanup(curl_handle);
    curl_global_cleanup();
}

struct url_mem* allocate_memory() { //allocate memory and check it hasnt failed
    struct url_mem *chunk = malloc(sizeof(struct url_mem)); 
    if (!chunk || !(chunk->memory = malloc(1))) {
        fprintf(stderr, "Failed to allocate memory\n");
        free(chunk);
        return NULL;
    }
    chunk->size = 0;
    return chunk;
}

cJSON* parse_json(const char *response) { //take in json string and convert to cjson object
    cJSON *root = cJSON_Parse(response);
    if (!root) {
        fprintf(stderr, "Error parsing JSON: %s\n", cJSON_GetErrorPtr());
        return NULL;
    }
    return root;
}

double convert_currency(const char *from_currency, const char *to_currency, double amount) {
    struct url_mem *chunk = allocate_memory();
    if (!chunk) return -1;

    char url[256];
    snprintf(url, sizeof(url), "https://yfapi.net/v6/finance/quote?region=US&lang=en&symbols=%s%s%%3DX", from_currency, to_currency);

    curl_global_init(CURL_GLOBAL_DEFAULT);

    // Create the header string using the API key variable
    char header_string[256];
    snprintf(header_string, sizeof(header_string), "X-API-KEY: %s", YFAPI_API_KEY);

    // Append the header to the list
    struct curl_slist *headers = curl_slist_append(NULL, header_string);

    CURL *curl_handle = initialize_curl(chunk, url, headers);
    if (!curl_handle) {
        cleanup_curl(curl_handle, headers, chunk);
        return -1;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, headers, chunk);
        return -1;
    }

    cJSON *root = parse_json(chunk->memory);
    if (!root) {
        cleanup_curl(curl_handle, headers, chunk);
        return -1;
    }

    cJSON *quoteResponse = cJSON_GetObjectItem(root, "quoteResponse");
    cJSON *result = cJSON_GetObjectItem(quoteResponse, "result");
    if (!result || !cJSON_IsArray(result)) {
        fprintf(stderr, "Error: 'result' is missing or not an array\n");
        cJSON_Delete(root);
        cleanup_curl(curl_handle, headers, chunk);
        return -1;
    }

    cJSON *firstResult = cJSON_GetArrayItem(result, 0);
    cJSON *regularMarketPrice = cJSON_GetObjectItem(firstResult, "regularMarketPrice");
    if (!regularMarketPrice) {
        fprintf(stderr, "regularMarketPrice is missing from quote response\n");
        cJSON_Delete(root);
        cleanup_curl(curl_handle, headers, chunk);
        return -1;
    }

    double rate = regularMarketPrice->valuedouble;
    double converted_amount = amount * rate;

    cJSON_Delete(root);
    cleanup_curl(curl_handle, headers, chunk);
    return converted_amount;
}

HistoricalData* fetch_historical_data(const char *from_currency, const char *to_currency, const char *period) {
    struct url_mem *chunk = allocate_memory(); // memory allocation
    if (!chunk) return NULL; 

    // get current time and set end date
    time_t now = time(NULL); // time in seconds (unix epoch) 
    struct tm *local_time = localtime(&now); // convert to local time
    char start_date[11], end_date[11]; 
    strftime(end_date, sizeof(end_date), "%Y-%m-%d", local_time); //set end date to current date

    if (!strcmp(period, "1D")) local_time->tm_mday -= 1; // set start date based on user selected period 
    else if (!strcmp(period, "1M")) local_time->tm_mon -= 1;
    else if (!strcmp(period, "3M")) local_time->tm_mon -= 3;
    else if (!strcmp(period, "YTD")) local_time->tm_mon = 0, local_time->tm_mday = 1;
    else if (!strcmp(period, "1Y")) local_time->tm_year -= 1;
    else local_time->tm_mday -= 30;  // use 30 days as default if period not recognized

    mktime(local_time); // normalize time
    strftime(start_date, sizeof(start_date), "%Y-%m-%d", local_time); // set start date

    // construct url
    char ticker[32];
    snprintf(ticker, sizeof(ticker), "%s%s.FOREX", from_currency, to_currency);

    char url[512];
    snprintf(url, sizeof(url), 
             "https://eodhd.com/api/eod/%s?from=%s&to=%s&order=d&api_token=%s&fmt=json", 
            ticker, start_date, end_date, EODHD_API_KEY);

    printf("Fetching data from %s to %s\n", start_date, end_date);
    //printf("Constructed url: %s\n", url);
    curl_global_init(CURL_GLOBAL_DEFAULT); // initialize curl and perform request
    CURL *curl_handle = initialize_curl(chunk, url, NULL);
    if (!curl_handle) {
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }

    cJSON *root = parse_json(chunk->memory); // convert to cjson object and extract data
    if (!root) return (cleanup_curl(curl_handle, NULL, chunk), NULL);
    int num_data_points = cJSON_GetArraySize(root);
    HistoricalData *data = malloc(sizeof(HistoricalData));
    data->rates = malloc(num_data_points * sizeof(double));
    data->dates = malloc(num_data_points * sizeof(char*));

    int count = 0; //iterate through cjson object and store close rates and their dates
    cJSON *date_data;
    cJSON_ArrayForEach(date_data, root) {
        cJSON *date = cJSON_GetObjectItem(date_data, "date");
        cJSON *close = cJSON_GetObjectItem(date_data, "close");
        
        if (date && close) {
            data->rates[count] = close->valuedouble;
            data->dates[count] = strdup(date->valuestring);
            count++;
        }
    }
    data->size = count; 

    cJSON_Delete(root); // cleanup and return result
    cleanup_curl(curl_handle, NULL, chunk);
    return data;
}

// map index names to  tickers
const char* map_index(const char *code) {
    if (strcmp(code, "FTSE 100") == 0) return "^FTSE";
    if (strcmp(code, "Nasdaq 100") == 0) return "NQ=F";
    if (strcmp(code, "S&P 500") == 0) return "^GSPC";
    if (strcmp(code, "Dow Jones") == 0) return "^DJI";
    if (strcmp(code, "DAX") == 0) return "^GDAXI";
    return NULL;
}

void free_historical_data(HistoricalData *data) {
    if (data) {
        free(data->rates);
        for (int i = 0; i < data->size; i++) {
            free(data->dates[i]);
        }
        free(data->dates);
        free(data);
    }
}

// define supported currencies and composites
const char* get_supported_currencies(int index) { 
    static const char* currencies[] = {"USD", "EUR", "GBP", "JPY" ,"CHF", "CAD", NULL};
    if (index >= 0 && currencies[index] != NULL) {
        return currencies[index];
    }
    return NULL;
}
const char** get_supported_exchanges() {
    static const char* exchanges[] = {"S&P 500", "Dow", "FTSE 100", "DAX", "Nasdaq 100", NULL};
    return exchanges;
}

void free_tickers(char **tickers, int count) {
    for (int i = 0; i < count; i++) {
        free(tickers[i]);
    }
    free(tickers);
}

void free_stock_historical_data(StockHistoricalData* data) {
    free(data);
}

StockHistoricalData* fetch_stock_historical_data(const char *symbol, const char *period, int *data_count) {
    // mem allocation and get start and end date
    struct url_mem *chunk = allocate_memory();
    if (!chunk) return NULL;

    time_t now = time(NULL);
    struct tm *local_time = localtime(&now);
    char start_date[11], end_date[11];
    strftime(end_date, sizeof(end_date), "%Y-%m-%d", local_time);

    if (!strcmp(period, "1D")) local_time->tm_mday -= 1; 
    else if (!strcmp(period, "1M")) local_time->tm_mon -= 1;
    else if (!strcmp(period, "3M")) local_time->tm_mon -= 3;
    else if (!strcmp(period, "YTD")) local_time->tm_mon = 0, local_time->tm_mday = 1;
    else if (!strcmp(period, "1Y")) local_time->tm_year -= 1;
    else local_time->tm_mday -= 30;
    mktime(local_time);
    strftime(start_date, sizeof(start_date), "%Y-%m-%d", local_time);

    // url construction
    char url[512];
    snprintf(url, sizeof(url), 
             "https://eodhistoricaldata.com/api/eod/%s?from=%s&to=%s&api_token=%s&fmt=json", 
             symbol, start_date, end_date, EODHD_API_KEY);

    // start curl and perform get request
    curl_global_init(CURL_GLOBAL_DEFAULT);
    CURL *curl_handle = initialize_curl(chunk, url, NULL);
    if (!curl_handle) {
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        printf("Error fetching historical data: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }

    // check if  data was returned
    if (chunk->size == 0) {
        printf("Error: No data returned from fetch_stock_data\n");
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }

    // parsing json response
    cJSON *json = parse_json(chunk->memory);
    if (!json) {
        printf("Error parsing JSON\n");
        printf("API Response: %s\n", chunk->memory);
        cleanup_curl(curl_handle, NULL, chunk);
        return NULL;
    }
    // iterate through json object and store data
    int num_data_points = cJSON_GetArraySize(json);
    StockHistoricalData *data = malloc(num_data_points * sizeof(StockHistoricalData));
    *data_count = num_data_points;

    for (int i = 0; i < num_data_points; i++) {
        cJSON *item = cJSON_GetArrayItem(json, i);
        strcpy(data[i].date, cJSON_GetObjectItem(item, "date")->valuestring);
        data[i].open = (cJSON_GetObjectItem(item, "open")->valuedouble);
        data[i].high = (cJSON_GetObjectItem(item, "high")->valuedouble);
        data[i].low = (cJSON_GetObjectItem(item, "low")->valuedouble);
        data[i].close = (cJSON_GetObjectItem(item, "close")->valuedouble);
        data[i].volume = cJSON_GetObjectItem(item, "volume")->valuedouble;
    }

    cJSON_Delete(json);
    cleanup_curl(curl_handle, NULL, chunk);
    return data;
}


PriceIndexData* get_price_index_data(const char *indicator, const char *country_code, const char *start_year, const char *end_year, int *data_count) {
    struct url_mem *chunk = allocate_memory(); // allocate memory
    if (!chunk) return NULL;

    // construct url
    char url[512];
    snprintf(url, sizeof(url), 
             "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/M.%s.PCPI_IX?startPeriod=%s&endPeriod=%s",
             country_code, start_year, end_year);

    // start curl and set up headers
    curl_global_init(CURL_GLOBAL_DEFAULT);
    struct curl_slist *headers = curl_slist_append(NULL, "Accept: application/json");
    CURL *curl_handle = initialize_curl(chunk, url, headers);
    if (!curl_handle) {
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    // parse json response and extract data
    cJSON *root = parse_json(chunk->memory);
    if (!root) {
        fprintf(stderr, "Error parsing JSON: %s\n", cJSON_GetErrorPtr());
        printf("API Response: %s\n", chunk->memory);
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    cJSON *data = cJSON_GetObjectItemCaseSensitive(root, "CompactData");
    data = cJSON_GetObjectItemCaseSensitive(data, "DataSet");
    data = cJSON_GetObjectItemCaseSensitive(data, "Series");
    data = cJSON_GetObjectItemCaseSensitive(data, "Obs");

    if (!data || !cJSON_IsArray(data)) {
        fprintf(stderr, "data not found in expected format\n");
        cJSON_Delete(root);
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    int num_data_points = cJSON_GetArraySize(data);
    PriceIndexData *price_data = malloc(num_data_points * sizeof(PriceIndexData));
    *data_count = num_data_points;

    for (int i = 0; i < num_data_points; i++) {
        cJSON *item = cJSON_GetArrayItem(data, i);
        cJSON *date = cJSON_GetObjectItemCaseSensitive(item, "@TIME_PERIOD");
        cJSON *value = cJSON_GetObjectItemCaseSensitive(item, "@OBS_VALUE");

        if (date && cJSON_IsString(date) && value && cJSON_IsString(value)) {
            strncpy(price_data[i].date, date->valuestring, sizeof(price_data[i].date) - 1);
            price_data[i].date[sizeof(price_data[i].date) - 1] = '\0';
            price_data[i].value = atof(value->valuestring);
        } else {
            fprintf(stderr, "Failed to parse data point %d\n", i);
        }
    }

    // cleanup and return result
    cJSON_Delete(root);
    cleanup_curl(curl_handle, headers, chunk);
    return price_data;
}

// get string of years between start and end year for (IMF) url construction
char* years_between(int start_year, int end_year) {
    if (start_year > end_year) return NULL;

    int num_years = end_year - start_year + 1;
    // calc buffer size required - 5 char per year (4 digits + comma) + 1 for null terminator
    int buffer_size = num_years * 5 + 1; 
    char *years_str = (char *)malloc(buffer_size);
    if (!years_str) {
        return NULL;
    }
    years_str[0] = '\0'; // set as empty string  for concatenation

    for (int year = start_year; year <= end_year; year++) {
        char year_str[5]; // 4 digits + null terminator
        snprintf(year_str, sizeof(year_str), "%d", year);
        strncat(years_str, year_str, buffer_size - strlen(years_str) - 1);
        if (year < end_year) {
            strncat(years_str, ",", buffer_size - strlen(years_str) - 1);
        }
    }

    return years_str;
}

const char* map_data_type(const char *data_type) {
    if (strcmp(data_type, "Nominal GDP") == 0) return "NGDPD"; // nominal GDP
    if (strcmp(data_type, "Real GDP Growth") == 0) return "NGDP_RPCH"; // real GDP growth
    if (strcmp(data_type, "GDP Per Capita") == 0) return "NGDPDPC"; // GDP per capita
    if (strcmp(data_type, "Unemployment Rate") == 0) return "LUR"; // unemployment rate
    
    if (strcmp(data_type, "Government debt") == 0) return "GGXWDG_NGDP";
    if (strcmp(data_type, "Government revenue") == 0) return "GGR_G01_GDP_PT";
    if (strcmp(data_type, "Government expenditure") == 0) return "G_X_G01_GDP_PT";

    if (strcmp(data_type, "GB") == 0) return "GBR";
    if (strcmp(data_type, "US") == 0) return "USA";
    if (strcmp(data_type, "FR") == 0) return "FRA";
    if (strcmp(data_type, "DE") == 0) return "DEU";
    if (strcmp(data_type, "JP") == 0) return "JPN";
    return NULL; 
}


EconomicData* get_economic_data(const char *country_code, const char *data_type, const char *start_year, const char *end_year, int *data_count) {
    struct url_mem *chunk = allocate_memory();
    if (!chunk) return NULL;

    curl_global_init(CURL_GLOBAL_ALL);

    char *periods = years_between(atoi(start_year), atoi(end_year));
    if (!periods) {
        curl_global_cleanup();
        return NULL;
    }

    const char *data_type_mapped = map_data_type(data_type); 
    const char *country_code_mapped = map_data_type(country_code);
    if (!(data_type_mapped || country_code_mapped)) {
        fprintf(stderr, "Invalid data type / country code: %s\n", data_type);
        free(periods);
        curl_global_cleanup();
        return NULL;
    }

    char url[512];
    snprintf(url, sizeof(url), 
        "https://www.imf.org/external/datamapper/api/v1/%s/%s?periods=%s",
        data_type_mapped, country_code_mapped, periods);

    free(periods); 

    struct curl_slist *headers = curl_slist_append(NULL, "Accept: application/json");
    CURL *curl_handle = initialize_curl(chunk, url, headers);
    if (!curl_handle) {
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    cJSON *json = parse_json(chunk->memory);
    if (!json) {
        fprintf(stderr, "Error parsing JSON\n");
        printf("API Response: %s\n", chunk->memory);
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    cJSON *values = cJSON_GetObjectItemCaseSensitive(json, "values");
    cJSON *data_json = cJSON_GetObjectItemCaseSensitive(values, data_type_mapped);
    cJSON *country = cJSON_GetObjectItemCaseSensitive(data_json, country_code_mapped);

    *data_count = cJSON_GetArraySize(country);
    EconomicData *economic_data = malloc(*data_count * sizeof(EconomicData));
    int index = 0;
    cJSON *year = NULL;
    cJSON_ArrayForEach(year, country) {
        snprintf(economic_data[index].year, sizeof(economic_data[index].year), "%s", year->string);
        economic_data[index].value = year->valuedouble;
        index++;
    }

    cJSON_Delete(json);
    cleanup_curl(curl_handle, headers, chunk);

    return economic_data;
}

const char* map_series_id(const char *code) {
    if (strcmp(code, "GB") == 0) return "IRLTLT01GBM156N";
    if (strcmp(code, "US") == 0) return "FEDFUNDS";
    if (strcmp(code, "FR") == 0) return "IRLTLT01FRM156N";
    if (strcmp(code, "DE") == 0) return "IRLTLT01DEQ156N";
    if (strcmp(code, "JP") == 0) return "INTDSRJPM193N";
    return NULL; 
}

InterestRateData* get_interest_rate_data(const char *series_id, const char *start_date, const char *end_date, int *data_count) {
    struct url_mem *chunk = allocate_memory();
    if (!chunk) return NULL;

    curl_global_init(CURL_GLOBAL_ALL);

    const char *series_id_mapped = map_series_id(series_id);
    if (!series_id_mapped) {
        fprintf(stderr, "Invalid series ID: %s\n", series_id);
        cleanup_curl(NULL, NULL, chunk);
        return NULL;
    }

    char url[512];
    snprintf(url, sizeof(url), 
        "https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json&observation_start=%s-01-01&observation_end=%s-06-06",
        series_id_mapped, FRED_API_KEY, start_date, end_date);

    struct curl_slist *headers = curl_slist_append(NULL, "Accept: application/json");
    CURL *curl_handle = initialize_curl(chunk, url, headers);
    if (!curl_handle) {
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    CURLcode res = curl_easy_perform(curl_handle);
    if (res != CURLE_OK) {
        fprintf(stderr, "couldn't start curl: %s\n", curl_easy_strerror(res));
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    cJSON *root = parse_json(chunk->memory);
    if (!root) {
        fprintf(stderr, "error parsing json: %s\n", cJSON_GetErrorPtr());
        printf("api  response: %s\n", chunk->memory);
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    cJSON *observations = cJSON_GetObjectItemCaseSensitive(root, "observations");
    if (!observations || !cJSON_IsArray(observations)) {
        fprintf(stderr, "observations not found in expected format\n");
        cJSON_Delete(root);
        cleanup_curl(curl_handle, headers, chunk);
        return NULL;
    }

    int num_data_points = cJSON_GetArraySize(observations);
    InterestRateData *interest_data = malloc(num_data_points * sizeof(InterestRateData));
    *data_count = num_data_points;

    for (int i = 0; i < num_data_points; i++) {
        cJSON *item = cJSON_GetArrayItem(observations, i);
        cJSON *date = cJSON_GetObjectItemCaseSensitive(item, "date");
        cJSON *value = cJSON_GetObjectItemCaseSensitive(item, "value");

        if (date && cJSON_IsString(date) && value && cJSON_IsString(value)) {
            strncpy(interest_data[i].date, date->valuestring, sizeof(interest_data[i].date) - 1);
            interest_data[i].date[sizeof(interest_data[i].date) - 1] = '\0';
            interest_data[i].value = atof(value->valuestring);
        } else {
            fprintf(stderr, "failed to   parse data point %d\n", i);
        }
    }
    cJSON_Delete(root);
    cleanup_curl(curl_handle, headers, chunk);
    return interest_data;
}

// finance api's do not offer data for retrieving stock tickers of constituents of composite index's 
// so we will have to webscrape the data from wikipedia

// webscrapping functions 

// get data from url and store in chunk
int fetch_data(const char *url, struct url_mem *chunk) {
    CURL *curl_handle;
    CURLcode res;

    chunk->memory = malloc(1);
    chunk->size = 0;

    curl_global_init(CURL_GLOBAL_ALL);
    curl_handle = curl_easy_init();
    if (curl_handle) {
        curl_easy_setopt(curl_handle, CURLOPT_URL, url);
        curl_easy_setopt(curl_handle, CURLOPT_WRITEFUNCTION, write_memory_callback);
        curl_easy_setopt(curl_handle, CURLOPT_WRITEDATA, (void *)chunk);
        res = curl_easy_perform(curl_handle);
        if (res != CURLE_OK) {
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
            return 1;
        }
        curl_easy_cleanup(curl_handle);
    }
    curl_global_cleanup();
    return 0;
}

// parse html and extract tickers
void parse_html(const char *html, const char *xpath_expr, char ***tickers, int *count) {
    //parse html
    htmlDocPtr doc = htmlReadMemory(html, strlen(html), NULL, NULL, HTML_PARSE_NOERROR | HTML_PARSE_NOWARNING);
    if (doc == NULL) {
        fprintf(stderr, "failure  parsing HTML\n");
        return;
    }
    // create xpath context
    xmlXPathContextPtr xpath_ctx = xmlXPathNewContext(doc);
    if (xpath_ctx == NULL) {
        fprintf(stderr, "failed to create xpath context\n");
        xmlFreeDoc(doc);
        return;
    }
    
    // evaluate xpath expression, get nodes
    xmlXPathObjectPtr xpath_obj = xmlXPathEvalExpression((const xmlChar *)xpath_expr, xpath_ctx);
    if (xpath_obj == NULL) {
        fprintf(stderr, "Failed to evaluate XPath expression\n");
        xmlXPathFreeContext(xpath_ctx);
        xmlFreeDoc(doc);
        return;
    }

    xmlNodeSetPtr nodes = xpath_obj->nodesetval;
    if (nodes == NULL) {
        fprintf(stderr, "no nodes found\n");
        xmlXPathFreeObject(xpath_obj);
        xmlXPathFreeContext(xpath_ctx);
        xmlFreeDoc(doc);
        return;
    }
    // allocate memory for tickers
    int max_count = nodes->nodeNr;
    *tickers = (char **)malloc(sizeof(char *) * max_count);
    if (*tickers == NULL) {
        fprintf(stderr, "failed to allocate memory for tickers\n");
        xmlXPathFreeObject(xpath_obj);
        xmlXPathFreeContext(xpath_ctx);
        xmlFreeDoc(doc);
        return;
    }
    // iterate through nodes and store tickers
    int valid_count = 0;
    for (int i = 0; i < max_count; i++) {
        xmlChar *ticker = xmlNodeGetContent(nodes->nodeTab[i]);
        if (ticker && strlen((char *)ticker) > 0) {
            (*tickers)[valid_count] = strdup((char *)ticker);
            if ((*tickers)[valid_count] == NULL) {
                fprintf(stderr, "failed to allocate memory for ticker\n");
                xmlFree(ticker);
                break;
            }
            valid_count++;
        }
        xmlFree(ticker);
    }
    *count = valid_count;
    // cleanup and free memory
    xmlXPathFreeObject(xpath_obj);
    xmlXPathFreeContext(xpath_ctx);
    xmlFreeDoc(doc);
}